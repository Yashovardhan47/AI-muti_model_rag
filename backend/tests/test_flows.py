def signup(client, email):
    response = client.post('/auth/register', json={'email': email, 'password': 'strong-password-123'})
    assert response.status_code == 201, response.text
    return response.json()

def headers(login):
    return {'Authorization': 'Bearer ' + login['access_token']}

def test_private_upload_search_chat_and_delete(client):
    one = signup(client, 'one@example.com')
    two = signup(client, 'two@example.com')
    h1, h2 = headers(one), headers(two)
    response = client.post('/files/upload', headers=h1, files={'file': ('risk.txt', b'Quarterly report: the cooling pump failed on Monday. Replace pump by Friday.', 'text/plain')})
    assert response.status_code == 201, response.text
    file_id = response.json()['id']
    listed = client.get('/files/list', headers=h1).json()
    assert listed[0]['status'] == 'ready', listed
    assert client.get('/files/list', headers=h2).json() == []
    assert client.get(f'/files/{file_id}/preview', headers=h2).status_code == 404
    assert client.post('/chat/query', headers=h2, json={'question': 'Which pump failed?', 'file_ids': [file_id]}).status_code == 404
    hits = client.get('/search', headers=h1, params={'q': 'cooling pump'}).json()
    assert hits and hits[0]['file_id'] == file_id
    assert client.get('/search', headers=h2, params={'q': 'cooling pump'}).json() == []
    response = client.post('/chat/query', headers=h1, json={'question': 'What happened to the pump?'})
    assert response.status_code == 200, response.text
    assert response.json()['citations'][0]['file_id'] == file_id
    session = response.json()['session_id']
    assert len(client.get(f'/chat/history/{session}', headers=h1).json()) == 2
    assert client.get(f'/chat/history/{session}', headers=h2).status_code == 404
    duplicate = client.post('/files/upload', headers=h1, files={'file': ('copy.txt', b'Quarterly report: the cooling pump failed on Monday. Replace pump by Friday.', 'text/plain')})
    assert duplicate.json()['duplicate'] is True
    assert client.delete(f'/files/{file_id}', headers=h1).status_code == 204
    assert client.get('/search', headers=h1, params={'q': 'cooling pump'}).json() == []

def test_auth_refresh_rotation_and_admin_boundary(client):
    user = signup(client, 'third@example.com')
    assert client.get('/admin/users', headers=headers(user)).status_code == 403
    assert client.get('/dashboard').status_code == 401
    first = client.post('/auth/refresh', json={'refresh_token': user['refresh_token']})
    assert first.status_code == 200, first.text
    assert client.post('/auth/refresh', json={'refresh_token': user['refresh_token']}).status_code == 401
    assert client.post('/auth/logout', headers=headers(first.json()), json={'refresh_token': first.json()['refresh_token']}).status_code == 200
    assert client.post('/auth/refresh', json={'refresh_token': first.json()['refresh_token']}).status_code == 401

def test_streaming_and_structured_log_summary(client):
    user = signup(client, 'log-reader@example.com')
    h = headers(user)
    content = b'{"records":[{"time":"2026-01-01","level":"error","pressure":10},{"time":"2026-01-02","level":"ok","pressure":11},{"time":"2026-01-03","level":"ok","pressure":50}]}'
    response = client.post('/files/upload', headers=h, files={'file': ('sensor.json', content, 'application/json')})
    assert response.status_code == 201, response.text
    assert client.get('/files/list', headers=h).json()[0]['status'] == 'ready'
    assert client.get('/search', headers=h, params={'q':'pressure error', 'tag':'json'}).json()
    stream = client.post('/chat/query/stream', headers=h, json={'question':'What pressure values appear in the log?'})
    assert stream.status_code == 200, stream.text
    assert 'event: delta' in stream.text and 'event: final' in stream.text
    assert 'sensor.json' in stream.text
