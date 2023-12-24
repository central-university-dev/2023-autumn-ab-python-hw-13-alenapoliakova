import os
from http import HTTPStatus
from wsgiref.simple_server import make_server
import psycopg2
from urllib.parse import parse_qs

# TODO: добавить данные
DATABASE_URL = "postgresql://username:password@localhost:5432/mydatabase"


def connect_db():
    return psycopg2.connect(DATABASE_URL)


def create_tables():
    with connect_db() as conn, conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT FALSE
        );
        """)


def get_tasks():
    with connect_db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, title, completed FROM tasks;")
        return cur.fetchall()


def get_task(task_id):
    with connect_db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, title, completed FROM tasks WHERE id = %s;", (task_id,))
        return cur.fetchone()


def create_task(title):
    with connect_db() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO tasks (title) VALUES (%s) RETURNING id;", (title,))
        return cur.fetchone()[0]


def update_task(task_id, title, completed):
    with connect_db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE tasks SET title = %s, completed = %s WHERE id = %s;", (title, completed, task_id))


def delete_task(task_id):
    with connect_db() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM tasks WHERE id = %s;", (task_id,))


def application(environ, start_response):
    path = environ['PATH_INFO']

    if path == '/':
        tasks = get_tasks()
        response_body = render_template('index.html', tasks=tasks)
    elif path == '/task':
        if environ['REQUEST_METHOD'] == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size)
            params = parse_qs(request_body.decode('utf-8'))
            title = params.get('title', [''])[0]
            if title:
                create_task(title)
        tasks = get_tasks()
        response_body = render_template('index.html', tasks=tasks)
    elif path.startswith('/task/'):
        task_id = int(path.split('/')[2])
        if environ['REQUEST_METHOD'] == 'GET':
            task = get_task(task_id)
            if task:
                response_body = render_template('task.html', task=task)
            else:
                start_response('404 Not Found', [('Content-type', 'text/plain; charset=utf-8')])
                return [b'Not Found']
        elif environ['REQUEST_METHOD'] == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size)
            params = parse_qs(request_body.decode('utf-8'))
            title = params.get('title', [''])[0]
            completed = params.get('completed', [''])[0] == 'on'
            update_task(task_id, title, completed)
            tasks = get_tasks()
            response_body = render_template('index.html', tasks=tasks)
        elif environ['REQUEST_METHOD'] == 'DELETE':
            delete_task(task_id)
            tasks = get_tasks()
            response_body = render_template('index.html', tasks=tasks)
    else:
        start_response('404 Not Found', [('Content-type', 'text/plain; charset=utf-8')])
        return [b'Not Found']

    start_response('200 OK', [('Content-type', 'text/html; charset=utf-8')])
    return [response_body.encode('utf-8')]


def render_template(template_name, **context):
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    template_path = os.path.join(templates_dir, template_name)
    with open(template_path, 'r', encoding='utf-8') as template_file:
        template_content = template_file.read()
    for key, value in context.items():
        template_content = template_content.replace(f'{{{{ {key} }}}}', str(value))
    return template_content


if __name__ == '__main__':
    create_tables()
    with make_server('', 8000, application) as httpd:
        print("Serving on port 8000...")
        httpd.serve_forever()
