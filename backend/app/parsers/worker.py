"""Private subprocess entry point. Only bounded JSON goes to stdout."""

import json
import logging
import resource
import sys


def main():
    resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024, 384 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    logging.disable(logging.CRITICAL)
    from app.parsers.docx import extract_docx
    from app.parsers.errors import ParseError
    from app.parsers.pdf import extract_pdf

    try:
        params = json.loads(sys.argv[2])
        data = sys.stdin.buffer.read(10485761)
        if len(data) > 10485760:
            raise ParseError(413, "File exceeds the upload limit.")
        parser = extract_pdf if sys.argv[1] == "pdf" else extract_docx
        char_limit = params.pop("max_chars")
        result = parser(data, **params)
        if len(result["text"]) > char_limit:
            raise ParseError(413, "Extracted text exceeds the processing limit.")
        output = {"result": result}
    except ParseError as exc:
        output = {"status": exc.status, "message": exc.message}
    except Exception:
        output = {
            "status": 422,
            "message": "Document unreadable or too complex. Export a fresh text-based PDF or DOCX.",
        }
    sys.stdout.write(json.dumps(output))


if __name__ == "__main__":
    main()
