import azure.functions as func
import logging


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name(name="HttpTrigger1")
@app.route(route="ieos_rag_poc_query", auth_level=func.AuthLevel.ANONYMOUS)
def ieos_rag_poc_query(req: func.HttpRequest) -> func.HttpResponse:
    from pgvector.psycopg2 import register_vector
    from sentence_transformers import SentenceTransformer
    import openai
    import psycopg2
    logging.info('Python HTTP trigger function processed a request.')

    model = SentenceTransformer("
                                ")
    def perform_similarity_search(dbname, user, password, host, port, query_embedding, top_k=5, collection_id=None):
        if collection_id is None:
            # Establish a connection to the PostgreSQL database
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port
            )

            # Register the vector type for this connection
            register_vector(conn)

            # Create a new cursor
            cur = conn.cursor()
            cur.execute('CREATE EXTENSION IF NOT EXISTS vector')

            # Prepare the SQL query for performing the similarity search
            # Assuming `embedding` column is stored as a vector type compatible with pgvector
            similarity_search_query = """
            SELECT document, (embedding <-> %(query_embedding)s) AS distance
            FROM rslt_embeddings
            ORDER BY distance
            LIMIT %(top_k)s;
            """

            # Execute the query
            cur.execute(similarity_search_query, {'query_embedding': query_embedding, 'top_k': top_k})

            # Fetch the results
            results = cur.fetchall()

            # Close the cursor and connection
            cur.close()
            conn.close()
            return results

        else:
            # Establish a connection to the PostgreSQL database
            conn = psycopg2.connect(
                dbname='postgres',
                user='user',
                password='nTier14!',
                host='flask-app-two-db.postgres.database.azure.com',
                port='5432'
            )

            # Register the vector type for this connection
            register_vector(conn)

            # Create a new cursor
            cur = conn.cursor()
            cur.execute('CREATE EXTENSION IF NOT EXISTS vector')

            # Prepare the SQL query for performing the similarity search
            # Assuming `embedding` column is stored as a vector type compatible with pgvector
            similarity_search_query = """
            SELECT document, (embedding <-> %(query_embedding)s) AS distance
            FROM rslt_embeddings
            WHERE collection_id = %(collection_id)s
            ORDER BY distance
            LIMIT %(top_k)s;
            """

            # Execute the query
            cur.execute(similarity_search_query,
                        {'query_embedding': query_embedding, 'top_k': top_k, 'collection_id': collection_id})

            # Fetch the results
            results = cur.fetchall()

            # Close the cursor and connection
            cur.close()
            conn.close()
            return results


    query = req.params.get('query')
    query_embedding = model.encode(query)
    results = perform_similarity_search('postgres', 'user', 'nTier14!', 'flask-app-two-db.postgres.database.azure.com', '5432', query_embedding, top_k=5)

    for document, distance in results:
        print(document, distance)

    template = f"""Use the following pieces of context to answer the question at the end.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    Use three sentences maximum and keep the answer as concise as possible.
    Always say "thanks for asking!" at the end of the answer.

    Question: {query}

    Here is the context
    Context: {results}
    """

    openai.api_key = ''

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        messages=[{"role": "user", "content": template}]
    )

    print(response.choices[0].message)

    return func.HttpResponse(response.choices[0].message.content)