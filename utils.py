def count_newlines(file_path):
    """
    Counts the number of newlines in a file.
    """

    def _make_gen(reader):
        b = reader(2**16)
        while b:
            yield b
            b = reader(2**16)

    with open(file_path, "rb") as f:
        return sum(buf.count(b"\n") for buf in _make_gen(f.raw.read))
