import os
import re
import argparse

def get_aggressive_fillers():
    """Returns a comprehensive regex pattern of fillers to maximize compression."""
    # Tiered categories for readability, joined into one aggressive regex
    tiers = [
        r"please|kindly|would|like|always|ensure|make|sure|try|simply|just|basically|essentially", # Fluff
        r"the|a|an|and|or|that|which|who|whom|whose|this|these|those|it|is|are|was|were|be|been|being", # Connectives
        r"of|for|with|about|against|between|into|through|during|before|after|above|below|to|from|up|down|in|out|on|off|over|under|again|further|then|once", # Prepositions
        r"i|me|my|mine|you|your|yours|we|us|our|ours|note|important|disclaimer|information|details|regarding|following|below" # Meta-references
    ]
    combined = "|".join(tiers)
    return re.compile(rf'\b({combined})\b', re.IGNORECASE)

def compress_content(content):
    """Applies aggressive minimization logic to markdown content."""
    # 1. Remove Markdown Comments
    content = re.sub(r'', '', content, flags=re.DOTALL)
    
    # 2. Remove Aggressive Fillers
    filler_pattern = get_aggressive_fillers()
    content = filler_pattern.sub('', content)
    
    # 3. Collapse whitespace and redundant newlines
    # Replaces 3+ spaces with 1 space
    content = re.sub(r'[ ]{3,}', ' ', content)
    # Replaces 3+ newlines with 2 newlines (preserves paragraph separation)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 4. Strip leading/trailing spaces from each line
    content = "\n".join([line.strip() for line in content.splitlines()])
    
    return content.strip()

def process_directory(target_folder):
    """Recursively processes .md files excluding .min.md."""
    target_folder = os.path.abspath(target_folder)
    print(f"🚀 Starting compression in: {target_folder}")
    
    processed_count = 0
    
    for root, _, files in os.walk(target_folder):
        for file in files:
            # Only process source .md files, ignore existing .min.md
            if file.endswith(".md") and not file.endswith(".min.md"):
                source_path = os.path.join(root, file)
                output_path = os.path.join(root, f"{os.path.splitext(file)[0]}.min.md")
                
                try:
                    with open(source_path, 'r', encoding='utf-8') as f:
                        original_text = f.read()
                    
                    compressed_text = compress_content(original_text)
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(compressed_text)
                    
                    processed_count += 1
                    print(f"✅ Compressed: {file} -> {os.path.basename(output_path)}")
                except Exception as e:
                    print(f"❌ Error processing {file}: {e}")

    print(f"\n✨ Done! Processed {processed_count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Maximize Markdown knowledge density for AI context.")
    parser.add_argument("folder", help="The target folder to process recursively")
    
    args = parser.parse_args()
    
    if os.path.isdir(args.folder):
        process_directory(args.folder)
    else:
        print(f"❌ Error: {args.folder} is not a valid directory.")