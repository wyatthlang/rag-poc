from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader
from sentence_transformers import SentenceTransformer

loader = Docx2txtLoader("WyattLang_Developer_Resume.docx")
documents = loader.load()
print(documents)

text_splitter = RecursiveCharacterTextSplitter(chunk_size = 450, chunk_overlap = 20)
texts = text_splitter.split_documents(documents)

model = SentenceTransformer("all-MiniLM-L6-v2")
doc_vectors = model.encode([t.page_content for t in texts])

from langchain.vectorstores.pgvector import PGVector
from pgvector.psycopg2 import register_vector
import psycopg2
import uuid
import json

from credentials import DBNAME, USER, PASSWORD, HOST, PORT

def setup_database_and_insert_embeddings(dbname, user, password, host, port, collection_name, metadata, embeddings,
                                         texts):
    # Establish a connection to the PostgreSQL database
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )

    print("creating new cursor")
    # Create a new cursor
    cur = conn.cursor()

    print("creating vector extension")
    cur.execute('CREATE EXTENSION IF NOT EXISTS vector')

    print("creating rslt collections statement")
    # SQL statement for creating the rslt_collections table if it does not exist
    create_collections_table_query = """
    CREATE TABLE IF NOT EXISTS rslt_collections (
        id UUID PRIMARY KEY,
        collection_name TEXT NOT NULL,
        metadata JSONB
    );
    """

    print("creating rslt embeddings statement")
    # SQL statement for creating the rslt_embeddings table if it does not exist
    create_embeddings_table_query = """
    CREATE TABLE IF NOT EXISTS rslt_embeddings (
        id UUID PRIMARY KEY,
        collection_id UUID,
        embedding vector,
        document TEXT,
        FOREIGN KEY (collection_id) REFERENCES rslt_collections (id)
    );
    """

    # Execute the CREATE TABLE statements
    cur.execute(create_collections_table_query)
    cur.execute(create_embeddings_table_query)

    # Generate a new UUID for the collection
    collection_id = uuid.uuid4()

    # Insert the new collection into rslt_collections
    insert_collection_query = """
    INSERT INTO rslt_collections (id, collection_name, metadata)
    VALUES (%s, %s, %s);
    """
    cur.execute(insert_collection_query, (str(collection_id), collection_name, json.dumps(metadata)))

    # Prepare the insert query for embeddings and documents
    insert_query = "INSERT INTO rslt_embeddings (id, collection_id, embedding, document) VALUES (%s, %s, %s, %s);"

    # Iterate over embeddings and texts simultaneously
    i = 0
    for embedding, text in zip(embeddings, texts):
        embedding_id = uuid.uuid4()
        # Insert the embedding and its corresponding text
        cur.execute(insert_query, (str(embedding_id), str(collection_id), embedding.tolist(), str(text.page_content)))
        print(f"document {i} of {len(texts)}")
        i += 1

    # Commit the transaction
    conn.commit()
    print("Embeddings inserted successfully.")

    # Close the cursor and connection
    cur.close()
    conn.close()

    return collection_id


COLLECTION_NAME = "wyatt_resume"

cid = setup_database_and_insert_embeddings(
    dbname=DBNAME,
    user=USER,
    password=PASSWORD,
    host=HOST,
    port=PORT,
    collection_name=COLLECTION_NAME,
    metadata={'creator': 'Wyatt Lang', 'description': "Wyatt Lang's Resume"},
    embeddings=doc_vectors,
    texts=texts
)