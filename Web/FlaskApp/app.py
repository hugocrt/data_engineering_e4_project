from flask import Flask, render_template, request
from flask_pymongo import PyMongo
from ..Elasticsearch_utils.elasticsearch_operations import *


def connect_to_mongodb(flaskapp):
    try:
        flaskapp.config['MONGO_URI'] = 'mongodb://localhost:27017/senscritique'
        mongo = PyMongo(flaskapp)
        collection = mongo.db.movies
        return collection

    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None


def retrieve_mongo_data(collection):
    projection = {'_id': 0}
    return list(collection.find({}, projection))


def retrieve_unique_fields(collection):
    # Get a sample document to determine the keys (fields)
    sample_document = collection.find_one({})

    # Exclude fields from the sample document that you want to ignore
    excluded_fields = {'title', 'poster', 'ranking', '_id'}
    fields_to_check = [field for field in sample_document if field not in excluded_fields]

    # Get distinct values for each field
    unique_fields = {field: collection.distinct(field) for field in fields_to_check}

    # Convert unique fields to list format
    unique_data_list = [
        {field: list(values)} for field, values in unique_fields.items() if values and all(value is not None for value in values)
    ]

    return unique_data_list


def launch_es(es_client, collection):
    clear_es_client(es_client)
    data = retrieve_mongo_data(collection)
    create_index(es_client, data)


app = Flask(__name__)
collection = connect_to_mongodb(app)
unique_fields = retrieve_unique_fields(collection)
print(unique_fields)

launch_es(es, collection)


@app.route('/')
def homepage():
    return render_template('index.html')


@app.route('/db', methods=['GET'])
def database_page():
    page_request = request.args.get('page', default=1, type=int)
    page_size = 5
    min_year = unique_fields[2]['publication_year'][0]
    max_year = unique_fields[2]['publication_year'][-1]

    min_year_request = request.args.get('min_year', default=f'{min_year}', type=str)
    max_year_request = request.args.get('max_year', default=f'{max_year}', type=str)
    sort_order_request = request.args.get('sort_order', default='asc', type=str)

    print(max_year_request, min_year_request)

    title_query = request.args.get('search_query', default='', type=str)
    search_params = {
        'title_query': title_query,
        'page_size': page_size,
        'page': page_request,
        'min_year': min_year_request,
        'max_year': max_year_request,
        'sort_order': sort_order_request,
    }

    hits, total_hits, info = search_movies('movies', **search_params)

    movie_data_list = [{key: value for key, value in hit['_source'].items()} for hit in hits]
    render_params = {
        'res': movie_data_list,
        'search_info': info,
        'page': page_request,
        'page_size': page_size,
        'total_hits': total_hits,
        'unique_fields': unique_fields
    }

    return render_template('db.html', **render_params)


@app.route('/map')
def map_page():
    return render_template('map.html')


@app.route('/analysis')
def analysis_page():
    return render_template('analysis.html')
