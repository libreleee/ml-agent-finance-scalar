from __future__ import annotations
import xml.etree.ElementTree as ET

def infer_row_tag(xml_path: str) -> str:
    """Infer rowTag for spark-xml by reading the first child element under the root.

    XML is like:
      <DocumentElement>
        <SOME_ROW_TAG>...</SOME_ROW_TAG>
        <SOME_ROW_TAG>...</SOME_ROW_TAG>
      </DocumentElement>
    """
    # iterparse is memory efficient
    for event, elem in ET.iterparse(xml_path, events=("start",)):
        # first element is root, second is first row
        if elem is None:
            continue
        # Skip the XML declaration; elem.tag gives first root encountered
        # We want the first child of the top root, so we do a second pass:
        break

    tree = ET.parse(xml_path)
    root = tree.getroot()
    if len(root) == 0:
        raise ValueError(f"No rows found in XML: {xml_path}")
    return root[0].tag
