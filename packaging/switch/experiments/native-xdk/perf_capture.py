from pathlib import Path


def game_capture(path):
    """Accept an explicit capture or a directory from a Switch or host replay."""
    path = Path(path)
    if path.is_dir():
        for name in ('game-perf.csv', 'alma-perf.csv', 'native-perf.csv'):
            if (path / name).is_file():
                return path / name
        raise FileNotFoundError(f'No game performance capture in {path}')
    return path
