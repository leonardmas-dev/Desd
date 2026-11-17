"""BRFN Camunda 8 inventory workers. Python standard library only.

Uses the same SQLite products table as the Validation demonstration worker.
Run with --test for offline tests, or --run with a configured Camunda REST endpoint.
"""
import argparse
from contextlib import closing
from datetime import date
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

JOB_TYPES = ('brfn.inventory.initialise', 'update-stock', 'unpublish-stock',
             'republish-product', 'deduct-inventory', 'check-restock-details')

class InventoryError(Exception):
    pass

def valid_quantity(value, *, allow_zero=True):
    if type(value) is not int or value < (0 if allow_zero else 1):
        raise InventoryError('stockQuantity must be a non-negative integer' if allow_zero else 'Quantity must be a positive integer')
    return value

def dates_from(values, old=None):
    old = old or {}
    start = values.get('seasonalStartDate', values.get('availableStart', old.get('availableStart')))
    end = values.get('seasonalEndDate', values.get('availableEnd', old.get('availableEnd')))
    try:
        if not isinstance(start, str) or not isinstance(end, str):
            raise ValueError('dates missing')
        s, e = date.fromisoformat(start), date.fromisoformat(end)
        if s > e: raise ValueError('start after end')
    except (ValueError, TypeError) as exc:
        raise InventoryError('Valid seasonal dates YYYY-MM-DD are required, start <= end') from exc
    return start, end

class Inventory:
    def __init__(self, filename):
        self.filename = str(filename)
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.filename)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS products (product_id TEXT PRIMARY KEY, submission_id TEXT, payload TEXT NOT NULL)')
            db.commit()

    def execute(self, job_type, values, today=None):
        today = today or date.today()
        if job_type == 'check-restock-details':
            try:
                valid_quantity(values.get('stockQuantity'))
                dates_from(values)
                return {'validationPassed': True}
            except InventoryError:
                return {'validationPassed': False}
        product_id = values.get('productId')
        if not isinstance(product_id, str) or not product_id.strip():
            raise InventoryError('productId is required')
        with closing(sqlite3.connect(self.filename, timeout=15)) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT submission_id, payload FROM products WHERE product_id=?', (product_id,)).fetchone()
            if job_type == 'brfn.inventory.initialise':
                quantity = valid_quantity(values.get('stockQuantity'), allow_zero=False)
                start, end = dates_from(values)
                if row:
                    # Validation may already have published the product; preserve its existing catalogue payload.
                    product = json.loads(row[1]); result = self._result(product)
                else:
                    available = start <= today.isoformat() <= end
                    product = {'productId': product_id, 'stockQuantity': quantity,
                               'availableStart': start, 'availableEnd': end,
                               'published': True, 'available': available,
                               'catalogueStatus': 'ACTIVE' if available else 'UNAVAILABLE_OFF_SEASON'}
                    db.execute('INSERT INTO products(product_id,submission_id,payload) VALUES(?,?,?)',
                               (product_id, values.get('submissionId'), json.dumps(product)))
                    result = self._result(product)
                db.commit(); return result
            if not row:
                raise InventoryError('Unknown productId: ' + product_id)
            product = json.loads(row[1]); quantity = product.get('stockQuantity')
            if job_type == 'update-stock':
                quantity = valid_quantity(values.get('stockQuantity'))
                start, end = dates_from(values, product)
                product.update(stockQuantity=quantity, availableStart=start, availableEnd=end)
                # Updating inventory never implicitly republishes a product.
                if quantity == 0:
                    product.update(available=False, catalogueStatus='UNAVAILABLE_OUT_OF_STOCK')
            elif job_type == 'deduct-inventory':
                deduction = valid_quantity(values.get('orderQuantity', 1), allow_zero=False)
                valid_quantity(quantity)
                if quantity < deduction:
                    raise InventoryError('Insufficient stock; order cannot be fulfilled')
                quantity -= deduction
                product['stockQuantity'] = quantity
                if quantity == 0:
                    product.update(available=False, catalogueStatus='UNAVAILABLE_OUT_OF_STOCK')
            elif job_type == 'unpublish-stock':
                if quantity != 0:
                    raise InventoryError('Cannot mark out of stock while quantity is nonzero')
                product.update(available=False, catalogueStatus='UNAVAILABLE_OUT_OF_STOCK')
            elif job_type == 'republish-product':
                valid_quantity(quantity, allow_zero=False)
                start, end = dates_from({}, product)
                if not (start <= today.isoformat() <= end):
                    raise InventoryError('Cannot republish outside the seasonal window')
                product.update(available=True, published=True, catalogueStatus='ACTIVE')
            else:
                raise InventoryError('Unsupported job type: ' + job_type)
            db.execute('UPDATE products SET payload=? WHERE product_id=?', (json.dumps(product), product_id))
            db.commit()
            return self._result(product)

    @staticmethod
    def _result(product):
        return {'productId': product['productId'], 'stockQuantity': product['stockQuantity'],
                'available': product.get('available', False),
                'catalogueStatus': product.get('catalogueStatus', 'UNKNOWN')}

class Client:
    def __init__(self, base, token):
        self.base = base.rstrip('/')
        if not self.base.endswith('/v2'): self.base += '/v2'
        self.token = token
        if not (self.base.startswith('https://') or self.base.startswith('http://localhost:') or self.base.startswith('http://127.0.0.1:')):
            raise ValueError('Use HTTPS for remote Camunda API')

    def post(self, path, payload):
        headers = {'Content-Type': 'application/json'}
        if self.token: headers['Authorization'] = 'Bearer ' + self.token
        request = Request(self.base + path, data=json.dumps(payload).encode(), headers=headers, method='POST')
        with urlopen(request, timeout=70) as response:
            return json.loads(response.read() or b'{}')

    def run(self, inventory):
        while True:
            for job_type in JOB_TYPES:
                jobs = self.post('/jobs/activation', {'type': job_type, 'worker': 'brfn-inventory',
                                 'timeout': 60000, 'maxJobsToActivate': 5, 'requestTimeout': -1}).get('jobs', [])
                for job in jobs:
                    key = job['jobKey']
                    try:
                        result = inventory.execute(job_type, job.get('variables', {}))
                        self.post(f'/jobs/{key}/completion', {'variables': result})
                    except InventoryError as exc:
                        # Match the BPMN boundary events on the two inventory operations.
                        error_codes = {
                            'deduct-inventory': 'INVENTORY_DEDUCTION_FAILED',
                            'update-stock': 'INVENTORY_UPDATE_FAILED',
                        }
                        if job_type in error_codes:
                            self.post(f'/jobs/{key}/error', {
                                'errorCode': error_codes[job_type],
                                'errorMessage': str(exc),
                                'variables': {'inventoryErrorMessage': str(exc), 'failedJobType': job_type},
                            })
                        else:
                            self.post(f'/jobs/{key}/failure', {'retries': 0, 'errorMessage': str(exc)})
                    except Exception as exc:
                        print('Worker error:', exc, file=sys.stderr)
                        self.post(f'/jobs/{key}/failure', {'retries': max(0, int(job.get('retries', 1)) - 1),
                                                          'errorMessage': str(exc), 'retryBackOff': 1000})
            time.sleep(0.5)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--db', default=os.environ.get('BRFN_CATALOGUE_DB', 'catalogue.db'))
    args = parser.parse_args()
    if not args.run: parser.error('Pass --run to start workers. Run tests separately with unittest.')
    api = os.environ.get('CAMUNDA_REST_URL')
    if not api: parser.error('Set CAMUNDA_REST_URL')
    Client(api, os.environ.get('CAMUNDA_BEARER_TOKEN', '')).run(Inventory(args.db))
