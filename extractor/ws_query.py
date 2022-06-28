
import json
import websockets


WS_START = json.dumps({
    'signal': 'start',
    'nbest': 1,
    'continuous_decoding': False,
})
WS_END = json.dumps({
    'signal': 'end'
})

WS_SERVERS = [
        'ws://127.0.0.1:8301',
        # 'ws://127.0.0.1:8302',
        # 'ws://127.0.0.1:8303',
        # 'ws://127.0.0.1:8304',
        # 'ws://127.0.0.1:8305',
        # 'ws://127.0.0.1:8306',
        # 'ws://127.0.0.1:8307',
        # 'ws://127.0.0.1:8308',
        ]
WS_INDEX = 0


def get_ws():
    global WS_INDEX
    svr = WS_SERVERS[WS_INDEX]
    WS_INDEX += 1
    WS_INDEX %= len(WS_SERVERS)
    return svr


async def ws_rec(data):
    texts = []
    ws = get_ws()
    conn = await websockets.connect(ws)
    # async with websockets.connect(ws) as conn:
    # step 1: send start
    await conn.send(WS_START)
    ret = await conn.recv()
    # step 2: send audio data
    await conn.send(data)
    # step 3: send end
    await conn.send(WS_END)
    # step 3: receive result
    i = 0
    while 1:
        i += 1
        ret = await conn.recv()
        # print('ws recv loop', i, ret)
        ret = json.loads(ret)
        if ret['type'] == 'final_result':
            nbest = json.loads(ret['nbest'])
            text = nbest[0]['sentence']
            texts.append(text)
        elif ret['type'] == 'speech_end':
            # print('=======', ret)
            break
    try:
        await conn.close()
    except Exception as e:
        # this except has no effect
        # print(e)
        pass
    return ''.join(texts)
