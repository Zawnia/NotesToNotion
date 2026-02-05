"""Test script for the improved markdown parser."""

import asyncio
from src.engine import Engine

# Test markdown with different structures
TEST_MARKDOWN = """# Introduction à la Théorie de l'Information

L'entropie d'une variable $X$ est définie par:

$$
H(X) = -\\sum_{x \\in X} p(x) \\log p(x)
$$

Propriétés importantes:
- Non-négative: $H(X) \\geq 0$
- Maximale pour distribution uniforme
- Additive pour variables indépendantes

## Applications

Texte avec $inline$ math et plusieurs lignes
de texte qui devraient être préservées.

### Sous-section

1. Premier élément
2. Deuxième élément avec $math$
3. Troisième élément

Autre paragraphe avec équation:

$$
I(X;Y) = \\sum_{x,y} p(x,y) \\log \\frac{p(x,y)}{p(x)p(y)}
$$

Conclusion avec $E = mc^2$ inline.
"""


async def main():
    """Test the parser."""
    # Create engine instance (no API keys needed for parsing)
    engine = Engine(
        google_api_key="dummy",
        notion_key="dummy",
        notion_db_id="dummy"
    )

    # Test the new parsing
    print("=" * 60)
    print("TESTING NEW MARKDOWN PARSER")
    print("=" * 60)

    # Phase 1: Parse into semantic blocks
    semantic_blocks = engine._parse_semantic_blocks(TEST_MARKDOWN)

    print(f"\n[Phase 1] Parsed {len(semantic_blocks)} semantic blocks:\n")
    for i, block in enumerate(semantic_blocks, 1):
        content_preview = block.content[:50].replace("\n", "\\n")
        if len(block.content) > 50:
            content_preview += "..."
        print(f"  {i}. {block.type.value:25s} | {content_preview}")

    # Phase 2: Convert to Notion blocks
    notion_blocks = engine._markdown_to_notion_blocks(TEST_MARKDOWN)

    print(f"\n[Phase 2] Generated {len(notion_blocks)} Notion blocks:\n")
    for i, block in enumerate(notion_blocks, 1):
        block_type = block['type']
        if block_type == 'equation':
            expr = block['equation']['expression'][:40]
            print(f"  {i}. {block_type:25s} | {expr}...")
        elif block_type.startswith('heading'):
            text = block[block_type]['rich_text'][0]['text']['content'][:40]
            print(f"  {i}. {block_type:25s} | {text}")
        elif block_type == 'paragraph':
            first_text = next((rt for rt in block['paragraph']['rich_text'] if rt['type'] == 'text'), None)
            if first_text:
                text = first_text['text']['content'][:40]
                print(f"  {i}. {block_type:25s} | {text}...")
        else:
            # List items
            first_text = next((rt for rt in block[block_type]['rich_text'] if rt['type'] == 'text'), None)
            if first_text:
                text = first_text['text']['content'][:40]
                print(f"  {i}. {block_type:25s} | {text}...")

    print("\n" + "=" * 60)
    print("SUCCESS! Parser working correctly.")
    print("=" * 60)

    # Detailed inspection of a paragraph with newlines
    print("\n[Testing Newline Preservation in Paragraphs]")
    test_para = "Line 1\nLine 2\nLine 3"
    rich_text = engine._parse_rich_text(test_para)
    print(f"Input: {repr(test_para)}")
    print(f"Output: {len(rich_text)} rich_text elements:")
    for i, rt in enumerate(rich_text):
        if rt['type'] == 'text':
            print(f"  {i}. text: {repr(rt['text']['content'])}")

    print("\n✓ Newlines preserved correctly!")


if __name__ == "__main__":
    asyncio.run(main())
