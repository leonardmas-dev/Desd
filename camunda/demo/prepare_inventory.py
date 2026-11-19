"""Prepare a local demo copy of the reviewed Inventory model and restock form."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "camunda/runtime/sprint2"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    model = (ROOT / "models/inventory.bpmn").read_text()
    before = (
        '<bpmn:scriptTask id="Task_UpdateStockRecord" name="Update Stock Record">\n'
        '      <bpmn:extensionElements>\n'
        '        <zeebe:script expression="=stockQuantity + restockQuantity" resultVariable="stockQuantity" />\n'
        '      </bpmn:extensionElements>\n'
        '      <bpmn:incoming>F_ValidRestock</bpmn:incoming>\n'
        '      <bpmn:outgoing>F_CheckSeasonalAvailability</bpmn:outgoing>\n'
        '    </bpmn:scriptTask>'
    )
    after = (
        before.replace("bpmn:scriptTask", "bpmn:serviceTask")
        .replace('<zeebe:script expression="=stockQuantity + restockQuantity" resultVariable="stockQuantity" />',
                 '<zeebe:taskDefinition type="brfn.inventory.update-stock" retries="3" />')
    )
    if model.count(before) != 1:
        raise SystemExit("Inventory update task changed. Review the new model before preparing the demo.")
    (OUT / "inventory-demo.bpmn").write_text(model.replace(before, after))
    form = json.loads((ROOT / "Forms 2/ProducerRestockForm.form").read_text())
    if form["id"] != "ProduerRestockForm":
        raise SystemExit("Restock form ID changed. Review the model and form together.")
    form["id"] = "ProducerRestockForm"
    (OUT / "ProducerRestockForm.form").write_text(json.dumps(form, indent=2) + "\n")


if __name__ == "__main__":
    main()
