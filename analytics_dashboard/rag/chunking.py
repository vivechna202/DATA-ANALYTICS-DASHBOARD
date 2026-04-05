def chunk_text(text, chunk_size=10):
    """
    Split text by lines (better for tables)
    Removes empty lines
    """
    lines = text.split("\n")

    # Remove empty lines
    lines = [line.strip() for line in lines if line.strip() != ""]

    chunks = []

    for i in range(0, len(lines), chunk_size):
        chunk = "\n".join(lines[i:i + chunk_size])
        chunks.append(chunk)

    return chunks