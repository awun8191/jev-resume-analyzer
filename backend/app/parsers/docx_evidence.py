"""Inspect Word metadata without pretending to know rendered coordinates."""
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile

from defusedxml.ElementTree import fromstring

from app.parsers.errors import ParseError

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def text_of(element):
    return "".join(t.text or "" for t in element.iter(W + "t"))


def extract_docx_evidence(data):
    spans, links, pages = [], [], []
    with ZipFile(BytesIO(data)) as archive:
        names = set(archive.namelist())
        styles = {}
        defaults = None
        if "word/styles.xml" in names:
            root = fromstring(archive.read("word/styles.xml"))
            styles = {s.get(W + "styleId"): s for s in root.findall(W + "style")}
            defaults = root.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")

        def properties(style_id, visited=None):
            visited = set() if visited is None else visited
            if style_id in visited or style_id not in styles:
                return []
            visited.add(style_id)
            style = styles[style_id]
            parent = style.find(W + "basedOn")
            return ([style.find(W + "rPr")] + properties(
                parent.get(W + "val") if parent is not None else None, visited))

        def value(props, tag, attr):
            for prop in props:
                child = prop.find(W + tag) if prop is not None else None
                if child is not None and child.get(W + attr) is not None:
                    return child.get(W + attr)
            return None

        parts = ["word/document.xml"] + sorted(n for n in names if
            n.startswith(("word/header", "word/footer")) and n.endswith(".xml"))
        for part in parts:
            root = fromstring(archive.read(part))
            relpath = str(PurePosixPath(part).parent / "_rels" /
                          (PurePosixPath(part).name + ".rels"))
            rels = {}
            if relpath in names:
                rels = {r.get("Id"): r for r in fromstring(archive.read(relpath))}
            for paragraph in root.iter(W + "p"):
                pstyle = paragraph.find(f"{W}pPr/{W}pStyle")
                style_id = pstyle.get(W + "val") if pstyle is not None else "Normal"
                alignment = paragraph.find(f"{W}pPr/{W}jc")
                for run in paragraph.findall(W + "r") + paragraph.findall(f"{W}hyperlink/{W}r"):
                    text = text_of(run)
                    if not text:
                        continue
                    rstyle = run.find(f"{W}rPr/{W}rStyle")
                    props = [run.find(W + "rPr")] + properties(
                        rstyle.get(W + "val") if rstyle is not None else None)
                    props += properties(style_id) + [defaults]
                    size = value(props, "sz", "val")
                    spans.append({"id": f"s{len(spans)}", "text": text,
                                  "location": PurePosixPath(part).stem,
                                  "font_name": value(props, "rFonts", "ascii"),
                                  "font_size_pt": float(size) / 2 if size else None,
                                  "alignment": alignment.get(W + "val")
                                  if alignment is not None else None})
                for link in paragraph.findall(W + "hyperlink"):
                    rel = rels.get(link.get(R + "id"))
                    target = rel.get("Target") if rel is not None else link.get(W + "anchor")
                    links.append({"label": text_of(link), "target": target,
                                  "kind": "external" if rel is not None and
                                  rel.get("TargetMode") == "External" else
                                  "internal" if target else "unresolved"})
            if part == "word/document.xml":
                for index, section in enumerate(root.iter(W + "sectPr"), 1):
                    size, margin = section.find(W + "pgSz"), section.find(W + "pgMar")
                    def points(element, attribute):
                        raw = element.get(W + attribute) if element is not None else None
                        return float(raw) / 20 if raw is not None else None
                    margins = [points(margin, a) for a in ("left", "top", "right", "bottom")]
                    pages.append({"number": index, "width_pt": points(size, "w"),
                                  "height_pt": points(size, "h"),
                                  "margins_pt": margins if None not in margins else None,
                                  "margin_kind": "configured" if None not in margins
                                  else "not_assessed"})
        if len(spans) > 5000 or len(links) > 500:
            raise ParseError(413, "Document metadata exceeds the processing limit.")
    return {"source_format": "docx", "pages": pages, "spans": spans, "links": links,
            "limitations": ["Page records describe sections, not rendered pages.",
                             "Exact positions and visual appearance: not assessed.",
                             "Missing or theme-dependent fonts: not assessed.",
                             "Field-code hyperlinks and unsupported run containers: not assessed.",
                             "Link destinations were extracted, not visited."]}
