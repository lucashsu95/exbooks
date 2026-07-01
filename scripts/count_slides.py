#!/usr/bin/env python3
with open('docs/presentation-0701.md', 'r') as f:
    content = f.read()

lines = content.split('\n')
in_code_block = False
slides = []
for i, line in enumerate(lines):
    if line.strip().startswith('```'):
        in_code_block = not in_code_block
        continue
    if not in_code_block and line.startswith('# '):
        slides.append((i+1, line.strip()))

print(f'Total slides: {len(slides)}')
for num, title in slides:
    print(f'{num}: {title}')
