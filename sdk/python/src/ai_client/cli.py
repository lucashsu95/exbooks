"""CLI：`ai-ask "你的問題"`。"""

from __future__ import annotations

import sys

from .factory import create_client


def main() -> None:
    if len(sys.argv) > 1:
        prompt = sys.argv[1]
    else:
        prompt = sys.stdin.read().strip()
    if not prompt:
        print('用法: ai-ask "你的問題"', file=sys.stderr)
        sys.exit(1)
    try:
        print(create_client().complete(prompt, max_tokens=2048))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
