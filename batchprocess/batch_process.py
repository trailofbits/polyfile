import csv
import json
import os
import platform
import shutil
import subprocess
import tempfile
import zipfile

import sqlite3


def get_exec_path(cmd):
    return subprocess.check_output(['/usr/bin/env', 'which', cmd]).decode('utf-8').strip()


def get_gnu_util(name, cmdtest=None):
    path = get_exec_path(name)
    if cmdtest is not None and not isinstance(cmdtest, list):
        cmdtest = list(cmdtest)
    if cmdtest is not None and subprocess.call([path] + cmdtest, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL):
        return get_exec_path(f'g{name}')
    else:
        return path


SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
TIME_PATH = get_gnu_util('time', cmdtest=[None, '--version'][platform.system() == 'Darwin'])
DEFAULT_DB_NAME = 'batch_process.db'

conn = None
def get_connection(db_path=None):
    if db_path is None:
        db_path = DEFAULT_DB_NAME
    global conn
    if conn is None:
        conn = sqlite3.connect(db_path)

        conn.execute('''CREATE TABLE IF NOT EXISTS pdfs (
filename TEXT,
start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
command TEXT NOT NULL,
timeout INTEGER NULL,
end TIMESTAMP NULL,
timed_out INTEGER NULL,
retcode INTEGER NULL,
stdout TEXT NULL,
stderr TEXT NULL,
json TEXT NULL,
timing TEXT NULL,
UNIQUE (filename, command) ON CONFLICT REPLACE
)''')
    return conn


def read_if_exists(path):
    try:
        with open(path, 'rb') as f:
            return f.read()
    except IOError:
        return None

# TODO: Register a SIGTERM handler to kill the Python child


def process_pdf(path, timeout_seconds=60*3):
    command = 'pdfinfo.py'
    cur = get_connection().cursor()
    filename = os.path.basename(path)
    row = cur.execute("SELECT start, retcode, timeout, timed_out FROM pdfs WHERE filename = ? AND command = ?",
                      (filename, command)).fetchone()
    if row is not None:
        if row[1] == 0:
            sys.stderr.write(f"Skipping {filename} because it was already processed on {row[0]!s}.\n")
            return
        elif row[3]:
            if row[2] <= timeout_seconds:
                sys.stderr.write(f"{filename} was already processed on {row[0]!s}, but timed out after {row[2]} seconds. Trying again...")
            else:
                sys.stderr.write(f"Skipping {filename} because it timed out after {row[2]} seconds on {row[0]!s}.\n")
                return
        elif row[1] is None:
            sys.stderr.write(f"{filename} was already processed on {row[0]!s}, but did not complete. Trying again...")
        else:
            sys.stderr.write(f"{filename} was already processed on {row[0]!s}, but failed with error code {row[1]}. Trying again...")
    else:
        sys.stderr.write(f"Processing {filename}...")
    sys.stderr.flush()
    with tempfile.TemporaryDirectory(dir=os.path.expanduser('~'), prefix='.tapptmp') as tmpdir:
        timing_file = tempfile.NamedTemporaryFile(dir=tmpdir, delete=False)
        stdout_file = tempfile.NamedTemporaryFile(dir=tmpdir, delete=False)
        stderr_file = tempfile.NamedTemporaryFile(dir=tmpdir, delete=False)
        pdf_file = os.path.join(tmpdir, filename)
        try:
            timing_file.close()
            shutil.copy(path, pdf_file)
            conn.execute("INSERT OR REPLACE INTO pdfs (filename, command, timeout) VALUES (?, ?, ?)",
                         (filename, command, timeout_seconds))
            conn.commit()
            process = subprocess.Popen(
                [
                    TIME_PATH, '-o', timing_file.name,
                    'python3', os.path.join(SCRIPT_DIR, 'pdfinfo.py'), filename
                ],
                cwd=tmpdir,
                stderr=stderr_file, stdout=stdout_file
            )
            interrupt = False
            timed_out = False
            try:
                retcode = process.wait(timeout_seconds)
            except subprocess.TimeoutExpired:
                sys.stderr.write(" Timed Out!\n")
                retcode = 0xFFFF
                timed_out = True
            except KeyboardInterrupt:
                sys.stderr.write("\n")
                interrupt = True

            if timed_out or interrupt:
                sys.stderr.write(f"Waiting for PID {process.pid} to die...")
                sys.stderr.flush()
                process.kill()
                # Make sure the process actually dies
                process.wait()
                sys.stderr.write(f"\r{' ' * 30}\r")
                sys.stderr.flush()
            stderr_file.close()
            stdout_file.close()
            if interrupt:
                sys.exit(1)
            elif timed_out:
                pass
            elif retcode == 0:
                sys.stderr.write(" Done.\n")
            else:
                sys.stderr.write(f" Error {retcode}!\n")
                sys.stderr.buffer.write(read_if_exists(stdout_file.name))
                sys.stderr.buffer.write(read_if_exists(stderr_file.name))
            conn.execute("""UPDATE pdfs SET
end = CURRENT_TIMESTAMP,
timed_out = ?,
retcode = ?,
stdout = ?,
stderr = ?,
json = ?,
timing = ?
WHERE filename = ? AND command = ?""", (
                timed_out,
                retcode,
                read_if_exists(stdout_file.name),
                read_if_exists(stderr_file.name),
                read_if_exists(stdout_file.name),
                read_if_exists(timing_file.name),
                filename,
                command
            ))
            conn.commit()
        finally:
            for tmpfile in (timing_file.name, stdout_file.name, stderr_file.name, pdf_file):
                if os.path.exists(tmpfile):
                    os.unlink(tmpfile)


def process_zip(path):
    with zipfile.ZipFile(path, "r") as f:
        for name in f.namelist():
            if name[-4:] == '.pdf':
                with tempfile.TemporaryDirectory() as tmpdir:
                    f.extract(name, tmpdir)
                    process_pdf(os.path.join(tmpdir, name))


def to_csv(db_path=None, out=None):
    if db_path is None:
        db_path = DEFAULT_DB_NAME
    if not os.path.exists(db_path):
        sys.stderr.write(f"Error opening database at {db_path}\n\n")
        return False
    if out is None:
        out = sys.stdout
    cur = get_connection(db_path).cursor()
    command = 'pdfinfo.py'
    columns = None
    c = csv.writer(out, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    for row in cur.execute(
            "SELECT filename, json, timing FROM pdfs WHERE command = ? AND retcode = 0", (command,)).fetchall():
        info = json.loads(row[1])
        if columns is None:
            columns = ('filename', 'timing') + tuple(info.keys())
            c.writerow(columns)
        if isinstance(row[2], bytes):
            timing = row[2].decode('utf-8').strip().replace('\n', ' ')
        else:
            timing = row[2]
        c.writerow([row[0], timing] + [info[col] for col in columns[2:]])
    return True


if __name__ == '__main__':
    import sys

    print_usage = len(sys.argv) < 2

    if not print_usage:
        if sys.argv[1] == '--csv':
            if len(sys.argv) > 3:
                print_usage = True
            else:
                if len(sys.argv) > 2:
                    path = sys.argv[2]
                else:
                    path = None
                print_usage = not to_csv(path)
        else:
            for path in sys.argv[1:]:
                if path[-4:] == '.zip':
                    process_zip(path)
                else:
                    process_pdf(path)

    if print_usage:
        sys.stderr.write(f"""Usage:
    {sys.argv[0]} PDF_OR_ZIP [PDF_OR_ZIP ...])    Saves results to a sqlite3 database called `batch_process.db`
                                                  in the current directory

    {sys.argv[0]} --csv [DB_PATH]                 Converts the given results database to a CSV printed to STDOUT

""")
        exit(1)
