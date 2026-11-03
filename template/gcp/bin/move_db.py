"""Read every document out of one emulator database, or write them into another.

A cloud export restores under the database it came from (``my-app``, ``test``),
but the app reads ``(default)`` on the emulator. ``bin/move_to_default.sh``
runs this twice in throwaway emulators: ``dump`` in one that imported the
export, ``load`` into ``(default)`` of an empty one that then saves. Two
emulators, because an emulator that imported a database always saves that
database again, even after its documents are deleted.

It refuses to run unless pointed at an emulator.

Usage:
    python move_db.py dump DATABASE FILE
    python move_db.py load FILE
"""

import os
import pickle
import sys
from typing import Any

from google.cloud import firestore

BATCH_SIZE = 400

# One entry per document: its path (collection/doc[/sub/doc...]) and fields.
Docs = list[tuple[str, dict[str, Any]]]


def client(database: str) -> firestore.Client:
    """Build a client for one emulator database.

    :param database: The database id.
    :return: The client.
    :raises SystemExit: When not pointed at an emulator.
    """
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        sys.exit("FIRESTORE_EMULATOR_HOST is not set; refusing to touch the cloud.")
    return firestore.Client(project=os.environ["GCLOUD_PROJECT"], database=database)


def read_collection(collection: firestore.CollectionReference, out: Docs) -> None:
    """Append a collection's documents, and their subcollections', to ``out``.

    :param collection: The collection to read.
    :param out: The list to append to.
    """
    for doc in collection.stream():
        out.append((doc.reference.path, doc.to_dict() or {}))
        for sub in doc.reference.collections():
            read_collection(sub, out)


def dump(database: str, path: str) -> None:
    """Write every document in ``database`` to a file.

    :param database: The named database the export restored into.
    :param path: The file to write.
    :raises SystemExit: When the database is empty.
    :side effects: Writes ``path``.
    """
    docs: Docs = []
    for collection in client(database).collections():
        before = len(docs)
        read_collection(collection, docs)
        print(f"  {collection.id}: {len(docs) - before}")
    if not docs:
        sys.exit(f"Database '{database}' is empty in the export; nothing to copy.")
    with open(path, "wb") as f:
        pickle.dump(docs, f)
    print(f"Read {len(docs)} documents from '{database}'.")


def load(path: str) -> None:
    """Write the documents in a file into ``(default)``.

    :param path: The file ``dump`` wrote.
    :side effects: Writes the emulator's ``(default)`` database.
    """
    with open(path, "rb") as f:
        docs: Docs = pickle.load(f)
    target = client("(default)")
    batch = target.batch()
    for count, (doc_path, data) in enumerate(docs, start=1):
        batch.set(target.document(doc_path), data)
        if count % BATCH_SIZE == 0:
            batch.commit()
            batch = target.batch()
    batch.commit()
    print(f"Wrote {len(docs)} documents into (default).")


if __name__ == "__main__":
    match sys.argv[1:]:
        case ["dump", database, path]:
            dump(database, path)
        case ["load", path]:
            load(path)
        case _:
            sys.exit(__doc__)
