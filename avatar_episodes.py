#%%
# Importing libraries...
import requests
from bs4 import BeautifulSoup as bs
#%%
# Used to get links for each episode dialog...
def get_episode_links(url,base_url):
    # Getting page information
    html = requests.get(url).content
    # Narrowing it to a list of links
    data = bs(html,'html.parser').find_all('b')
    links = []
    for item in data:
        # Filter for only the ones we need
        tag = item.findChildren('a',href=lambda x: x and '/wiki/' in x)
        if len(tag) != 0:
            unpacked_tag = tag[0]
            # We don't need the first part of the link
            links.append(base_url+unpacked_tag['href'][6:])
    return links

#%%
# Used to get table rows with dialog...
def get_episode_html(link):
    tran_html = requests.get(link).content
    parsed_html = bs(tran_html,'html.parser')

    # Episode title
    title_words = (parsed_html
        .find('h1',id='firstHeading')
        .getText()
        .split())
    title = title_words[0][11:]
    for word in title_words[1:]:
        if word != '(episode)':
            title += ' '+word

    # 'find_all' and 'find' only searches the top level of the html you give it,
    # so it will ignore your item if it is nested. I know that for these pages,
    # the 'tables' I want are the only ones on the top level that have
    # class="wikitable".
    tables = (parsed_html
        .find_all('table',
        class_=lambda x:x=='wikitable'))
    # From here, I only have the tables I want, so I just extract what I want.
    table_bodies = []
    for item in tables:
        table_bodies += item.find_all('tbody')
    table_rows = []
    for item in table_bodies:
        # Using + on two lists unpacks the contents of the second and appends 
        # them to the first. 'find_all' returns a list, so this becomes:
        # ['what','I','have'] + ['new','from','find_all'] =
        # ['what','I','have','new','from','find_all']
        table_rows += item.find_all('tr')
    return title, table_rows

#%%
# Used to format transcript...
def get_episode_transcript(title,table):
    # Getting episode title
    yield 'Episode: '+title+'\n'
    # Get speaker if it is dialog
    for row in table:
        is_dialogue = True
        table_header = row.findChildren('th')
        if len(table_header) != 0:
            yield '\n'+table_header[0].getText()[:-1]+':\n'
        else:
            yield '\n'
            is_dialogue = False

        # If there is no name, we find two 'td's so we have to skip the first,
        # empty one to get 'row_entry'.
        td = row.findChildren('td')
        if len(td) == 1:
            choice = 0
        else:
            choice = 1
        
        # Marking action-descriptions in dialog for formatting in next step
        row_entry = (td[choice]
            .getText()
            .replace('\n','')
            .replace('[','*[')
            .replace(']',']*')
            .split('*'))
        
        # To hold re-built phrase
        text_list = []
        for item in row_entry:
            # Using check decided earlier. If it is dialog, it gets formatted.
            if is_dialogue:
                # Removes blank lines
                if len(item) != 0:
                    # Using split on * chars separates actions and dialog. We
                    # put quotes around dialog and then put the line back
                    # together with the actions.
                    if item[0] != '[':
                        letters = list(item)
                        if letters[0] == ' ':
                            letters[0] = '"'
                        else:
                            letters.insert(0,'"')
                        if letters[-1] == ' ':
                            letters[-1] = '"'
                        else:
                            letters.append('"')
                        phrase = ''.join(letters)
                        text_list.append(phrase)   
                    else:
                        text_list.append(item)
            # Using check decided earlier. If it's not dialog, it does not get
            # formatted because it is a scene description.
            else:
                text_list.append(item)
        # Re-building row_entry, then splitting it into list of 'words' in 
        # 'entry'.
        entry = (' '.join(text_list)).split()

        # Builds lines to not be over 72 chars in length
        tr_row = ''
        for word in entry:
            if len(tr_row+word+' ') > 72:
                yield tr_row[:-1]+'\n'
                tr_row = word+' '
            else:
                tr_row+=word+' '
        if len(tr_row) != 0:
            yield tr_row[:-1]+'\n'
    # Adds space between episodes.
    yield '\n\n'


# %%
# Functional-style combining of other functions...
def get_lines(link_list):
    for link in link_list:
        title, table = get_episode_html(link)
        for line in get_episode_transcript(title,table):
            yield [line, link]

# %%
# Error handling functions...

# Try to remove unusable characters
def encode_fix(line,error):
    # Used to check error type
    cant_map_char  = "'charmap' codec can't encode character "
    char_len = len(cant_map_char)
    # Correct by error type
    if str(error)[:char_len] == cant_map_char:
        return (line
            .replace(u'\u014d','o')
            .replace(u'\u200a','')
            .replace(u'\u200c','')
            .replace(u'\u200b','')
            .replace(u'\u200d',''))
    else:
        return (line
            .encode('ascii','ignore').decode())

# Used if error can't be fixed, line where error occurred will be skipped
def report_error(line, link, error):
    print('###############')
    print(link)
    print(line)
    print(str(error))
    print('###############')

# %%
# Writing transcript to file...
with open('avatar_the_last_airbender_transcript.txt','w') as file:

    # Getting links to transcripts
    url = 'https://avatar.fandom.com/wiki/List_of_Avatar:_The_Last_Airbender_episodes'
    base_url = 'https://avatar.fandom.com/wiki/Transcript:'
    links = get_episode_links(url,base_url)

    # Additional note: since get_lines and get_episode transcript use 'yield' 
    # instead of 'return', the result of get_lines is a list in progress, so
    # you can use the function call like an iterable like I did here in the 
    # 'for' loop.
    for line in get_lines(links):
        # The try/except statement is just to catch an error. 'txt' files 
        # cannot have unicode characters so they have to be dealt with, in which
        # case 'encode_fix' is called in UnicodeEncodeError.
        try:
            # Think of line[0] as just line that is yielded from get_lines. The 
            # entire list 'line' is two items, but the second one is only used
            # report other errors in Exception.
            file.write(line[0])
        except UnicodeEncodeError as error:
            try:
                file.write(encode_fix(line[0], error))
            except Exception as breaking_error:
                report_error(line[0],line[1],breaking_error)

# %%
