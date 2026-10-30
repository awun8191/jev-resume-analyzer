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
    from app.parsers.run import parse

    try:
        params = json.loads(sys.argv[2])
        # Backstop for the request boundary, which admits at most 4 MB of content.
        data = sys.stdin.buffer.read(4000001)
        if len(data) > 4000000:
            from app.parsers.errors import ParseError

            raise ParseError(413, "File exceeds the upload limit.")
        output = parse(sys.argv[1], data, params)
    except Exception:
        output = {
            "status": 422,
            "message": "Document unreadable or too complex. Export a fresh text-based PDF or DOCX.",
        }
    sys.stdout.write(json.dumps(output))


if __name__ == "__main__":
    main()
