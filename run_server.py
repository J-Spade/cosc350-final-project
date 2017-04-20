import BaseHTTPServer
import cgi
import os
import random
import math
import string
import copy
import threading

webpage_text = ''

STOPWORD = 'BOGON'

#       key        come-befores       come-afters
DEFAULT_DICTIONARY = {STOPWORD: ([(STOPWORD, 1)], [(STOPWORD, 1)])}
dictionary = copy.deepcopy(DEFAULT_DICTIONARY)

wordcounts = {STOPWORD: 0}
paircounts = {STOPWORD: 0}
sentences_ever = 0

dictLock = threading.Lock()

class MarkovReqHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write(webpage_text)

    def do_HEAD(self):
        self._set_headers()
    
    def do_POST(self):
        form = cgi.FieldStorage(
                fp = self.rfile,
                headers = self.headers,
                environ = {'REQUEST_METHOD':'POST',
                           'CONTENT_TYPE':self.headers['Content-Type']
                          })

        self._set_headers()
        message = ''
        if (len(form) > 0):
            message = form['text'].value.lower()
        print 'Interpreting message...'
        interpret_message(message)
        print 'Generating response...'
        response = generate_chain(message)
        self.wfile.write(webpage_text.replace('<!-- Response text goes here -->', response))
        save_dictionary()



def runserver(server_class=BaseHTTPServer.HTTPServer,
        handler_class=MarkovReqHandler,
        port=int(os.environ.get('PORT', 5000))):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting httpd...'
    httpd.serve_forever()


def save_dictionary():
    """Save the dictionary to disk"""
    dictLock.acquire()
    output = open('Markov_Dict.pkl', 'w')
    pickle.dump(dictionary, output)
    output.close()
    dictLock.release()

def load_dictionary():
    """Load the dictionary file"""
    dictLock.acquire()
    input = open('Markov_Dict.pkl', 'r')
    dictionary = pickle.load(input)
    input.close()
    dictLock.release()

def interpret_message(message):
    """Interprets a message"""
    
    print 'Acquiring Lock'
    dictLock.acquire()
    words = message.split()
    words.append(STOPWORD)
    words.insert(0, STOPWORD)

    sentences_ever = sentences_ever + 1

    print 'Doing keys'
    for word in words:
        if not (wordcounts.has_key(word)):
            wordcounts[word] = 0
        wordcounts[word] = wordcounts.get(word) + 1

    index = 0
    word = words[index]
    # cannot be out of range; at least (stop, stop, word, stop, stop)
    wordpair = words[index] + u' ' + words[index + 1]

    print 'Adding counts'
    while True:
        try:
            next = words[index + 2]
            nextpair = words[index + 1] + u' ' + words[index + 2]
        except IndexError:
            # this means we got to the end of the sentence
            break

        if not (paircounts.has_key(wordpair)):
            paircounts[wordpair] = 0
        paircounts[wordpair] = paircounts.get(wordpair) + 1

        print 'after'

        # add 'next' as a word that comes after 'wordpair'
        if dictionary.has_key(wordpair):
            temp = dictionary.get(wordpair)[1]
            wordindex = word_index_in_list(next, temp)
            if wordindex == -1:
                temp.append((next, 1))
            else:
                prevcount = temp[wordindex][1]
                temp[wordindex] = (next, prevcount + 1)
        else:
            dictionary[wordpair] = ([], [(next, 1)])

        print 'before'

        # add 'word' as a word that comes before 'nextpair'
        if dictionary.has_key(nextpair):
            othertemp = dictionary.get(nextpair)[0]
            wordindex = word_index_in_list(word, othertemp)
            if wordindex == -1:
                othertemp.append((word, 1))
            else:
                prevcount = othertemp[wordindex][1]
                othertemp[wordindex] = (word, prevcount + 1)

        else:
            dictionary[nextpair] = ([(word, 1)], [])

        index = index + 1
        word = words[index]
        wordpair = word + u' ' + words[index + 1]

    dictLock.release()


def generate_chain(message):
    """Generates a Markov chain from a message"""
 
    dictLock.acquire()

    words = message.split()
    words.append(STOPWORD)
    words.insert(0, STOPWORD)

    if len(words) < 2:
        return ''

    # try to guess which word is the most important
    subject = STOPWORD
    confidence = 0

    for word in words:
        if wordcounts.has_key(word):
            tfidf = tf_idf(word, words, wordcounts, sentences_ever)
            if tfidf > confidence:
                confidence = tfidf
                subject = word

    # pick a word pair we've seen used with that word before as a seed
    pairs = []
    for wordpair in paircounts:
        temp = wordpair.split()
        if (temp[0] == subject) or ((len(temp) > 1) and (temp[1] == subject)):
            pairs.append((wordpair, paircounts.get(wordpair)))

    seed = choose_word_from_list(pairs)

    chain = ''
 
    # forwards
    wordpair = seed
    if dictionary.has_key(wordpair):
        chain = wordpair
    #print wordpair
    while (wordpair.split()[1] != STOPWORD) and (dictionary.has_key(wordpair)):
        wordpair = wordpair.split()[1] + u' ' + \
                    choose_word_from_list(dictionary.get(wordpair)[1])
        #print wordpair
        chain = chain + u' ' + wordpair.split()[1]
    # backwards
    wordpair = seed
    if dictionary.has_key(wordpair) and wordpair.split()[0] != STOPWORD:
        wordpair = choose_word_from_list(
            dictionary.get(wordpair)[0]) + \
            u' ' + wordpair.split()[0]
    # so we don't have the seed twice

    while (wordpair.split()[0] != STOPWORD) and (dictionary.has_key(wordpair)):
        #print wordpair
        chain = wordpair.split()[0] + u' ' + chain
        wordpair = choose_word_from_list(
            dictionary.get(wordpair)[0]) + \
            u' ' + wordpair.split()[0]

    dictLock.release()

    return chain.replace(STOPWORD, u'')


def word_index_in_list(findword, word_list):
    """Get the index of a word in a list"""
    for index in range(len(word_list)):
        if word_list[index][0] == findword:
            return index
    return -1

def choose_word_from_list(word_list):
    """Pick a random word from a list"""
    total = 0
    stops = [0]
    for pair in word_list:
        total = total + pair[1]
        stops.append(total)
    if sum > 1:
        rand = random.randint(1, total)
    else:
        rand = 1
    for index in range(len(stops)):
        if rand <= stops[index]:
            return word_list[index - 1][0]
    return word_list[0][0]

def tf_idf(keyword, words, counts, totalcount):
    
    count = 0
    for word in words:
        if keyword == word:
            count = count + 1
    
    tf = float(count)/len(words)

    idf = math.log(float(totalcount) / counts.get(keyword))

    return tf*idf

############### 
#             #
# RUN SCRIPT: #
#             #
###############

print 'Loading chatbox.html...'
try:
    webpage = open('chatbox.html', 'r')
    webpage_text = webpage.read()
    webpage.close()
except IOError:
    print 'Unable to load chatbox.html'

print 'Loading dictionary...'
try:
    load_dictionary()

    print 'Counting words...'            
    for wordpair in dictionary:

        temp = wordpair.split()
        uses = 0
        for temp in dictionary.get(wordpair)[0]:
            uses = uses + temp[1]
        paircounts[wordpair] = uses

        tally = 0
        for prev in dictionary.get(wordpair)[0]:
            tally += prev[1]

        first = wordpair.split()[0]
        if not (wordcounts.has_key(first)):
            wordcounts[first] = 0
        wordcounts[first] = wordcounts.get(first) + tally

        if wordpair != STOPWORD:
            second = wordpair.split()[1]
            if not (wordcounts.has_key(second)):
                wordcounts[second] = 0
            wordcounts[second] = wordcounts.get(second) + tally

    sentences_ever = wordcounts.get(STOPWORD)

except IOError:
    print 'Dictionary could not be loaded.'
    dictLock.release()

runserver()