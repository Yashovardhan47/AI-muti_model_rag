from tests.test_flows import signup, headers


def test_versioned_search_comparison_and_evidence_access(client):
    owner, reader, stranger = [signup(client, email) for email in
                               ('version-owner@example.com', 'version-reader@example.com', 'version-stranger@example.com')]
    own, shared, hidden = headers(owner), headers(reader), headers(stranger)
    old = client.post('/files/upload', headers=own,
                      files={'file': ('assets.csv', b'asset,cost\nP-17,450\nP-18,300\n', 'text/csv')})
    assert old.status_code == 201, old.text
    first = old.json()['id']
    assert client.post(f'/files/{first}/access', headers=own, json={'email': 'version-reader@example.com'}).status_code == 201
    assert client.get(f'/files/{first}/preview', headers=shared).status_code == 200
    assert client.get(f'/files/{first}/evidence/unknown', headers=hidden).status_code == 404

    before = client.post('/chat/query', headers=shared, json={'question': 'What was the P-17 cost?', 'file_ids': [first]})
    assert before.status_code == 200, before.text
    session = before.json()['session_id']
    newer = client.post('/files/upload', headers=own,
                        data={'replace_file_id': first, 'ocr_languages': 'eng+hin'},
                        files={'file': ('assets.csv', b'asset,cost\nP-17,475\nP-18,300\n', 'text/csv')})
    assert newer.status_code == 201, newer.text
    second = newer.json()['id']
    assert newer.json()['version'] == 2
    listed = {item['id']: item for item in client.get('/files/list', headers=shared).json()}
    assert listed[first]['is_current'] is False and listed[second]['is_current'] is True
    assert listed[second]['read_only'] and listed[second]['ocr_languages'] == 'eng+hin'
    assert len(client.get(f'/files/{second}/versions', headers=shared).json()) == 2
    current = client.get('/search', headers=shared, params={'q': 'P-17 cost'})
    assert current.status_code == 200 and current.json()[0]['file_id'] == second
    all_versions = client.get('/search', headers=shared, params={'q': 'P-17 cost', 'include_versions': True}).json()
    assert {hit['file_id'] for hit in all_versions} == {first, second}
    evidence = next(hit for hit in current.json() if hit['location'].startswith('sheet CSV rows'))
    located = client.get(f"/files/{second}/evidence/{evidence['chunk_id']}", headers=shared)
    assert located.status_code == 200 and located.json()['locator']['row_start'] == 1
    assert client.get(f"/files/{second}/evidence/{evidence['chunk_id']}", headers=hidden).status_code == 404
    changes = client.get('/files/compare', headers=shared, params={'left_id': first, 'right_id': second})
    assert changes.status_code == 200, changes.text
    assert any(change['record'] == 'p-17' and change['left']['value'] == '450' and
               change['right']['value'] == '475' for change in changes.json()['changes'])
    assert client.get('/files/compare', headers=hidden, params={'left_id': first, 'right_id': second}).status_code == 404
    history = client.get(f'/chat/history/{session}', headers=shared).json()[1]
    assert history['citations'][0]['source_state'] == 'superseded'
    assert history['citations'][0]['available'] is True

    restored = client.post('/files/upload', headers=own, data={'replace_file_id': second},
                           files={'file': ('assets.csv', b'asset,cost\nP-17,450\nP-18,300\n', 'text/csv')})
    assert restored.status_code == 201, restored.text
    assert restored.json()['version'] == 3 and restored.json()['duplicate'] is False
    assert client.get(f'/files/{first}/versions', headers=shared).json()[0]['id'] == restored.json()['id']

    assert client.delete(f'/files/{second}/access/{reader["user"]["id"]}', headers=own).status_code == 204
    assert client.get('/files/list', headers=shared).json() == []
    assert client.get(f'/files/{second}/preview', headers=shared).status_code == 404
    redacted = client.get(f'/chat/history/{session}', headers=shared).json()[1]
    assert redacted['content'].startswith('Answer removed because')
    assert redacted['citations'][0]['excerpt'] == ''


def test_reconcile_replays_vectors_and_requires_admin(client):
    user = signup(client, 'reconcile-user@example.com')
    response = client.post('/files/upload', headers=headers(user),
                           files={'file': ('repair.txt', b'Index replay proves the committed source can be found.', 'text/plain')})
    assert response.status_code == 201, response.text
    assert client.post('/admin/reconcile', headers=headers(user)).status_code == 403
    from app.services.reconcile import reconcile
    summary = reconcile()
    assert summary['vector_refs_replayed'] >= 1
    assert response.json()['id'] not in summary['missing_sources']
