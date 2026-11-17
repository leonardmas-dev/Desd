import json
from contextlib import closing
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from inventory_worker import Inventory, InventoryError

class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'catalogue.db')
        self.inv = Inventory(self.db)
        self.data = {'productId':'p1','stockQuantity':4,'availableStart':'2026-01-01','availableEnd':'2026-12-31'}
        self.inv.execute('brfn.inventory.initialise', self.data, date(2026,11,17))

    def tearDown(self): self.tmp.cleanup()

    def record(self):
        with closing(sqlite3.connect(self.db)) as db:
            return json.loads(db.execute('SELECT payload FROM products WHERE product_id=?',('p1',)).fetchone()[0])

    def test_save_update(self):
        self.inv.execute('update-stock', dict(self.data, stockQuantity=7), date(2026,11,17))
        self.assertEqual(self.record()['stockQuantity'], 7)

    def test_deduct_and_unpublish(self):
        self.inv.execute('deduct-inventory', {'productId':'p1','orderQuantity':4})
        self.inv.execute('unpublish-stock', {'productId':'p1'})
        self.assertFalse(self.record()['available'])
        self.assertEqual(self.record()['catalogueStatus'], 'UNAVAILABLE_OUT_OF_STOCK')

    def test_republish(self):
        self.inv.execute('update-stock', dict(self.data, stockQuantity=0))
        self.inv.execute('update-stock', dict(self.data, stockQuantity=6))
        self.inv.execute('republish-product', {'productId':'p1'}, date(2026,11,17))
        self.assertTrue(self.record()['available'])

    def test_republish_off_season_fails(self):
        with self.assertRaises(InventoryError):
            self.inv.execute('republish-product', {'productId':'p1'}, date(2027,1,1))

    def test_no_overselling(self):
        with self.assertRaises(InventoryError):
            self.inv.execute('deduct-inventory', {'productId':'p1','orderQuantity':5})
        self.assertEqual(self.record()['stockQuantity'],4)

    def test_invalid_details(self):
        self.assertFalse(self.inv.execute('check-restock-details',dict(self.data,stockQuantity=-2))['validationPassed'])

    def test_initialise_idempotent(self):
        self.inv.execute('brfn.inventory.initialise', dict(self.data,stockQuantity=9))
        self.assertEqual(self.record()['stockQuantity'],4)

if __name__ == '__main__': unittest.main()
