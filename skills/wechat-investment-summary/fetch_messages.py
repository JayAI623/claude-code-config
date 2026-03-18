#!/usr/bin/env python3
"""
Fetch and clean today's messages from WeChat investment groups.
Usage: python3 fetch_messages.py [--days 1] [--group "群名关键词"]
"""
import sqlite3, os, hashlib, zstandard, datetime, re, sys, argparse, subprocess

DB_DIR = os.path.expanduser('~/Desktop/微信相关/wechat-decrypt/decrypted/message')
CONTACT_DB = os.path.expanduser('~/Desktop/微信相关/wechat-decrypt/decrypted/contact/contact.db')
DECRYPT_DIR = os.path.expanduser('~/Desktop/微信相关/wechat-decrypt')

ALL_GROUPS = [
    ('26927313011@chatroom', 'RWA 贝版投资俱乐部'),
    ('26552422185@chatroom', '贝版投资俱乐部Creative Financing'),
    ('27899422963@chatroom', '贝版俱乐部 大饼铭文&L2'),
    ('25877913860@chatroom', '贝版 特斯拉投资'),
    ('27609622050@chatroom', '贝版 俱乐部AI群'),
    ('27173218763@chatroom', '贝版俱乐部股票交易群'),
    ('26729310942@chatroom', '贝版投资俱乐部西雅图群'),
    ('26421307056@chatroom', '贝版私人投资俱乐部'),
    ('25873310541@chatroom', '贝版投资俱乐部风投'),
    ('26734024923@chatroom', '贝版俱乐部 量子计算'),
    ('26045425768@chatroom', '贝版 贵金属逃顶群'),
    ('27191115774@chatroom', '贝版 太空经济'),
]

dctx = zstandard.ZstdDecompressor()

def decode_bytes(b):
    if isinstance(b, bytes):
        if b[:4] == b'\x28\xb5\x2f\xfd':
            try: return dctx.decompress(b).decode('utf-8', errors='replace')
            except: return ''
        return b.decode('utf-8', errors='replace')
    return str(b) if b else ''

def extract_text(raw):
    if not raw:
        return ''
    raw = raw.strip()
    if not raw.startswith('<?xml'):
        return raw

    title = re.search(r'<title>(.*?)</title>', raw, re.DOTALL)
    title = title.group(1).strip() if title else ''

    refer = re.search(r'<refermsg>(.*?)</refermsg>', raw, re.DOTALL)
    if refer:
        ref_block = refer.group(1)
        ref_content = re.search(r'<content>(.*?)</content>', ref_block, re.DOTALL)
        ref_nick = re.search(r'<displayname>(.*?)</displayname>', ref_block, re.DOTALL)
        ref_text = ''
        if ref_content:
            ref_text = re.sub(r'<[^>]+>', '', ref_content.group(1)).strip()[:60]
        nick = ref_nick.group(1).strip() if ref_nick else '?'
        if title:
            return f'↩[{nick}: {ref_text}] {title}'
        return ''

    if title:
        return title
    if re.search(r'<img ', raw):
        return '[图片]'
    if 'revokemsg' in raw:
        return ''
    return ''

def load_contacts():
    names = {}
    try:
        conn = sqlite3.connect(CONTACT_DB)
        for u, nick, remark in conn.execute("SELECT username, nick_name, remark FROM contact"):
            names[str(u)] = remark or nick or str(u)
        conn.close()
    except:
        pass
    return names

def fetch_group_messages(username, since_ts, names):
    table = 'Msg_' + hashlib.md5(username.encode()).hexdigest()
    dbs = [os.path.join(DB_DIR, f) for f in sorted(os.listdir(DB_DIR))
           if f.startswith('message_') and f.endswith('.db')
           and not f.endswith('-shm') and not f.endswith('-wal')]
    msgs = []
    for db_path in dbs:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                f'SELECT create_time, real_sender_id, message_content, compress_content '
                f'FROM "{table}" WHERE create_time >= ? ORDER BY create_time',
                (since_ts,)
            )
            for ts, sender, mc, cc in cur.fetchall():
                raw = decode_bytes(cc) if cc else decode_bytes(mc)
                text = extract_text(raw)
                if not text or text == '[图片]':
                    continue
                dt = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
                name = names.get(str(sender), str(sender))
                msgs.append((dt, name, text))
            conn.close()
        except:
            pass
    return msgs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=1)
    parser.add_argument('--group', type=str, default=None)
    parser.add_argument('--no-decrypt', action='store_true')
    args = parser.parse_args()

    if not args.no_decrypt:
        print('🔓 重新解密数据库...', flush=True)
        result = subprocess.run(['python3', 'decrypt_db.py'], cwd=DECRYPT_DIR, capture_output=True, text=True)
        last_line = [l for l in result.stdout.strip().split('\n') if l.strip()]
        if last_line:
            print(last_line[-1])

    now = datetime.datetime.now()
    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if args.days > 1:
        since -= datetime.timedelta(days=args.days - 1)
    since_ts = int(since.timestamp())

    names = load_contacts()

    groups = ALL_GROUPS
    if args.group:
        groups = [(u, n) for u, n in ALL_GROUPS if args.group in n]
        if not groups:
            print(f'未找到包含 "{args.group}" 的群')
            sys.exit(1)

    results = {}
    for username, group_name in groups:
        msgs = fetch_group_messages(username, since_ts, names)
        if msgs:
            results[group_name] = msgs

    if not results:
        print('今日无活跃群消息')
        sys.exit(0)

    print(f'\n=== 活跃群：{len(results)} 个 ===\n')
    for group_name, msgs in results.items():
        print(f'\n## {group_name}（{len(msgs)} 条）')
        for dt, sender, text in msgs:
            print(f'[{dt}] {sender}: {text}')

if __name__ == '__main__':
    main()
