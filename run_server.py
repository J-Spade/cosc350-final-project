import BaseHTTPServer
import cgi
import os
import random
import math
import string
import copy

webpage_text = ''

STOPWORD = 'BOGON'

#       key        come-befores       come-afters
DEFAULT_DICTIONARY = {STOPWORD: ([(STOPWORD, 1)], [(STOPWORD, 1)])}
dictionary = copy.deepcopy(DEFAULT_DICTIONARY)

wordcounts = {STOPWORD: 0}
paircounts = {STOPWORD: 0}
sentences_ever = 0


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
        self.interpret_message(message)
        response = self.generate_chain(message)
        self.wfile.write(webpage_text.replace('<!-- Response text goes here -->', response))



def runserver(server_class=BaseHTTPServer.HTTPServer,
        handler_class=MarkovReqHandler,
        port=int(os.environ.get('PORT', 5000))):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting httpd...'
    httpd.serve_forever()


def save_dictionary(self):
    """Save the dictionary to disk"""
    self.dictLock.acquire()
    output = open('Markov_Dict.pkl', 'w')
    pickle.dump(self.dictionary, output)
    output.close()
    self.dictLock.release()

def load_dictionary(self):
    """Load the dictionary file"""
    self.dictLock.acquire()
    input = open('Markov_Dict.pkl', 'r')
    self.dictionary = pickle.load(input)
    input.close()
    self.dictLock.release()

def interpret_message(self, message):
    """Interprets a message"""
    
    self.dictLock.acquire()
    words = message.split()
    words.append(self.STOPWORD)
    words.insert(0, self.STOPWORD)

    self.sentences_ever = self.sentences_ever + 1
    self.stats['sentences_ever'] = self.sentences_ever
    self.update_stats_file()

    # find URLs, neaten them up
    for i in range(0, len(words)):
        words[i] = clean_url(words[i])

    for word in words:
        if not (self.wordcounts.has_key(word)):
            self.wordcounts[word] = 0
        self.wordcounts[word] = self.wordcounts.get(word) + 1

    index = 0
    word = words[index]
    # cannot be out of range; at least (stop, stop, word, stop, stop)
    wordpair = words[index] + u' ' + words[index + 1]

    while True:
        try:
            next = words[index + 2]
            nextpair = words[index + 1] + u' ' + words[index + 2]
        except IndexError:
            # this means we got to the end of the sentence
            break

        if not (self.paircounts.has_key(wordpair)):
            self.paircounts[wordpair] = 0
        self.paircounts[wordpair] = self.paircounts.get(wordpair) + 1

        # add 'next' as a word that comes after 'wordpair'
        if self.dictionary.has_key(wordpair):
            temp = self.dictionary.get(wordpair)[1]
            wordindex = word_index_in_list(next, temp)
            if wordindex == -1:
                temp.append((next, 1))
            else:
                prevcount = temp[wordindex][1]
                temp[wordindex] = (next, prevcount + 1)
        else:
            self.dictionary[wordpair] = ([], [(next, 1)])


        # add 'word' as a word that comes before 'nextpair'
        if self.dictionary.has_key(nextpair):
            othertemp = self.dictionary.get(nextpair)[0]
            wordindex = word_index_in_list(word, othertemp)
            if wordindex == -1:
                othertemp.append((word, 1))
            else:
                prevcount = othertemp[wordindex][1]
                othertemp[wordindex] = (word, prevcount + 1)

        else:
            self.dictionary[nextpair] = ([(word, 1)], [])

        index = index + 1
        word = words[index]
        wordpair = word + u' ' + words[index + 1]

    
    self.dictLock.release()


def generate_chain(self, message):
    """Generates a Markov chain from a message"""
 
    self.dictLock.acquire()

    words = message.split()
    words.append(self.STOPWORD)
    words.insert(0, self.STOPWORD)

    # find URLs, neaten them up
    for i in range(0, len(words)):
        words[i] = clean_url(words[i])
    if '<{}>'.format(self.users[self.BOT_ID]) in words[1]:
        del words[1]

    if len(words) < 2:
        return ''


    # try to guess which word is the most important
    subject = self.STOPWORD
    confidence = 0

    for word in words:
        if self.wordcounts.has_key(word):
            tfidf = tf_idf(word, words, self.wordcounts, self.sentences_ever)
            if tfidf > confidence:
                confidence = tfidf
                subject = word

    # pick a word pair we've seen used with that word before as a seed
    pairs = []
    for wordpair in self.paircounts:
        temp = wordpair.split()
        if (temp[0] == subject) or ((len(temp) > 1) and (temp[1] == subject)):
            pairs.append((wordpair, self.paircounts.get(wordpair)))

    seed = choose_word_from_list(pairs)

    chain = ''
 
    # forwards
    wordpair = seed
    if self.dictionary.has_key(wordpair):
        chain = wordpair
    #print wordpair
    while (wordpair.split()[1] != self.STOPWORD) and (self.dictionary.has_key(wordpair)):
        wordpair = wordpair.split()[1] + u' ' + \
                    choose_word_from_list(self.dictionary.get(wordpair)[1])
        #print wordpair
        chain = chain + u' ' + wordpair.split()[1]
    # backwards
    wordpair = seed
    if self.dictionary.has_key(wordpair) and wordpair.split()[0] != self.STOPWORD:
        wordpair = choose_word_from_list(
            self.dictionary.get(wordpair)[0]) + \
            u' ' + wordpair.split()[0]
    # so we don't have the seed twice

    while (wordpair.split()[0] != self.STOPWORD) and (self.dictionary.has_key(wordpair)):
        #print wordpair
        chain = wordpair.split()[0] + u' ' + chain
        wordpair = choose_word_from_list(
            self.dictionary.get(wordpair)[0]) + \
            u' ' + wordpair.split()[0]

    self.dictLock.release()

    return chain.replace(self.STOPWORD, u'')


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
    self.load_dictionary()

    print 'Counting words...'            
    for wordpair in self.dictionary:

        temp = wordpair.split()
        uses = 0
        for temp in self.dictionary.get(wordpair)[0]:
            uses = uses + temp[1]
        self.paircounts[wordpair] = uses

        tally = 0
        for prev in self.dictionary.get(wordpair)[0]:
            tally += prev[1]

        first = wordpair.split()[0]
        if not (self.wordcounts.has_key(first)):
            self.wordcounts[first] = 0
        self.wordcounts[first] = self.wordcounts.get(first) + tally

        if wordpair != self.STOPWORD:
            second = wordpair.split()[1]
            if not (self.wordcounts.has_key(second)):
                self.wordcounts[second] = 0
            self.wordcounts[second] = self.wordcounts.get(second) + tally

    self.sentences_ever = self.wordcounts.get(self.STOPWORD)
    self.stats['sentences_ever'] = self.sentences_ever

except IOError:
    print 'Dictionary could not be loaded.'

runserver()