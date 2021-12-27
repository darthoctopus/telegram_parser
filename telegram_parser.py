import pandas as pd
import datetime
import html
from os.path import isfile, join

def parse_file(filename, timezone=0):

    TZ = datetime.timezone(datetime.timedelta(hours=timezone))

    with open(filename, 'r') as f:
        lines = f.readlines()

    sender = None
    state_machine = 0
    d = None

    # Finite state machine state list
    # 0: awaiting date of next item
    # 1: have received a date, awaiting either name of sender, text, or media descriptor
    # 2: message sender expected to change this line
    # 3: text message begun; now appending to message body until </div> received
    # 4: successful media_call; awaiting call direction and duration

    acc = []

    for l in lines:

        if state_machine == 0:
            if 'pull_right date details' in l:
                s = l[51:-3]
                try:
                    d = datetime.datetime(year=int(s[6:10]),
                        month=int(s[3:5]),
                        day=int(s[:2]),
                        hour=int(s[11:13]),
                        minute=int(s[14:16]),
                        second=int(s[17:19]),
                        tzinfo=TZ
                        )
                except ValueError:
                    continue
                else:
                    state_machine = 1
                    continue

        if state_machine == 1:

            if "from_name" in l:
                state_machine = 2
                continue

            if 'media_call' in l:
                if 'success' not in l:
                    acc.append({
                        'sender': sender,
                        'datetime': d,
                        'message': 'Missed Call',
                        'duration': 0
                        })
                    state_machine = 0
                    continue
                else:
                    state_machine = 4
                    continue

            if 'media_photo' in l:
                acc.append({
                    'sender': sender,
                    'datetime': d,
                    'message': 'Photo',
                    'duration': 0
                    })
                state_machine = 0
                continue

            if "<div class=\"text\">" in l:
                state_machine = 3
                s = ''
                continue

        if state_machine == 2:
            state_machine = 1
            if '<' in l: # filter e.g. names from forwarded messages
                continue

            # if the "last name" is not set in TG contact name, sender will end with space
            if l[-2] != ' ':
                sender = l[:-1]
            else:
                sender = l[:-2]
            continue

        if state_machine == 3:
            if "</div>" in l:
                acc.append({
                    'sender': sender,
                    'datetime': d,
                    'message': html.unescape(s)[:-1],
                    'duration': 0
                    })
                state_machine = 0
            else:
                s += l
            continue

        if state_machine == 4:
            if "seconds)" in l:
                duration = int(l.split("(")[1].split(" ")[0])
                acc.append({
                    'sender': sender,
                    'datetime': d,
                    'message': 'Call',
                    'duration': duration
                    })
                state_machine = 0
                continue

    return pd.DataFrame(acc)

def parse_folder(dir, **kwargs):
    i = 1
    acc = []
    while True:
        filename = join(dir, f"messages{'' if i == 1 else i}.html")
        if not isfile(filename):
            break
        acc.append(parse_file(filename, **kwargs))
        i += 1
    return pd.concat(acc, ignore_index=True)

if __name__ == "__main__":
    print(parse_folder("Telegram Desktop/ChatExport_2021-12-27"))