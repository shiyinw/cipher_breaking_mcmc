import numpy as np
import math, random, time, collections, pickle, itertools
random.seed(121)
import warnings
warnings.filterwarnings("ignore")
from multiprocessing import Pool
import traceback

SHORT_TEXT = 1000

P = np.zeros(shape=([28]))
with open("data/letter_probabilities.csv", "r") as f:
    line = f.readline()
    P = [float(x) for x in line[:-1].split(",")]
logP = np.log(P)

M = np.zeros(shape=([28, 28]))
with open("data/letter_transition_matrix.csv", "r") as f:
    lines = f.readlines()
    assert len(lines)==28, "The size of the alphabet is 28"
    for i in range(28):
        M[i, :] = [float(x) for x in lines[i].split(",")]
logM = np.log(M) # 0 exists

Alphabet = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r',
                         's', 't', 'u', 'v', 'w', 'x', 'y', 'z', ' ', '.']

idx2alpha = dict(zip(range(28), Alphabet))

with open("words.pickle", "rb") as f:
    words = pickle.load(f)

with open("dict.pickle", "rb") as f:
    words_dict = pickle.load(f)

def refine(content, words_dict):
    words = content.replace("\n", "").split(" ")
    low_freq_words = {}
    for a in ["k", "j", "z", "q", "x"]:
        low_freq_words[a] = [x for x in words if a in x]

    best_per = dict(zip(["k", "j", "z", "q", "x"], ["k", "j", "z", "q", "x"]))
    best_acc = 0

    for per in list(itertools.permutations(["k", "j", "z", "q", "x"])):
        pi = dict(zip(["k", "j", "z", "q", "x"], per))
        score = 0
        for a in ["k", "j", "z", "q", "x"]:
            score += len([x for x in low_freq_words[a] if x.replace(a, pi[a]) in words_dict[a]])
        if score >= best_acc:
            best_acc = score
            best_per = pi

    content = content.replace("k", "1")
    content = content.replace("j", "2")
    content = content.replace("z", "3")
    content = content.replace("q", "4")
    content = content.replace("x", "5")

    content = content.replace("1", best_per["k"])
    content = content.replace("2", best_per["j"])
    content = content.replace("3", best_per["z"])
    content = content.replace("4", best_per["q"])
    content = content.replace("5", best_per["x"])
    return content

def checkvalid(content):
    transition = collections.Counter()
    for i in Alphabet:
        transition[i] = collections.Counter()
    for i in range(1, len(content), 1):  # including /n
        transition[content[i - 1]][content[i]] += 1

    notrepeat = []  # ' ' & '.'
    for a in Alphabet:
        if (transition[a][a] == 0):
            notrepeat.append(a)

    set1 = []  # " "
    set2 = []  # "."
    for a in notrepeat:
        if (len(transition[a]) == 0):
            set2.append(a)
        elif (len(transition[a]) == 1 and list(transition[a].keys())[0] in notrepeat):
            set1.append(list(transition[a].keys())[0])
            set2.append(a)



    if (len(set(list(content[:-1]))) == 28):  # All the char have occurred. So we must have a ". " pair.
        return set2, set1
    else:
        return set2, notrepeat

class MCMC:
    def __init__(self, ciphertext):
        self.alphabet = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r',
                         's', 't', 'u', 'v', 'w', 'x', 'y', 'z', ' ', '.']
        alphabet = self.alphabet
        self.idx2alpha = dict(zip(range(28), self.alphabet))
        random.shuffle(alphabet)

        self.cur_f = dict(zip(alphabet, range(28)))
        self.ciphertext_transition = collections.Counter()
        for a in self.alphabet:
            self.ciphertext_transition[a] = collections.Counter()
        for i in range(1, len(ciphertext), 1): #including /n
            self.ciphertext_transition[ciphertext[i]][ciphertext[i-1]] += 1
        self.ciphertext = ciphertext
        self.set1, self.set2 = checkvalid(self.ciphertext)
        
    def Pf(self, code2idx):
        logPf = logP[code2idx[self.ciphertext[0]]]
        for a in self.alphabet:
            for b in self.alphabet:
                if self.ciphertext_transition[a][b]!=0:
                    if logM[code2idx[a], code2idx[b]] == -float('inf'):
                        return "not exist"
                    else:
                        logPf += self.ciphertext_transition[a][b] * logM[code2idx[a], code2idx[b]]
        
        return logPf

    def accept(self, newscore, oldscore):
        """
        :param newscore: log-likelihood
        :param oldscore: log-likelihood
        :return:
        """
        accept_bool = False
        if newscore == "not exist" and oldscore == "not exist":
            if random.random() < 0.5:
                accept_bool = True
        elif oldscore == "not exist":
            accept_bool = True
        elif newscore == "not exist":
            pass
        elif (newscore - oldscore) > 5:  # speed up for np.exp
            accept_bool = True
        elif random.random() < min(1, np.exp(newscore - oldscore)):
            accept_bool = True
        return accept_bool

    def generate_f(self, oldf, set1, set2):
        # set1: "."
        # set2 : " "
        a, b = random.sample(self.alphabet, 2)
        f2 = oldf.copy()
        f2[a] = oldf[b]
        f2[b] = oldf[a]
        for i, v in f2.items():
            if (v == 27 and i not in set1):
                candidate = random.sample(set1, k=1)[0]
                tmp = f2[i]
                f2[i] = f2[candidate]
                f2[candidate] = tmp
            if (v == 26 and i not in set2):
                candidate = random.sample(set2, k=1)[0]
                tmp = f2[i]
                f2[i] = f2[candidate]
                f2[candidate] = tmp
        return f2
    
    def decode(self):
        s = ""
        for c in self.ciphertext:
            s += self.idx2alpha[self.cur_f[c]]
        return s
    
    def run(self, runningtime=-1):
        if runningtime == -1:
            runningtime = min(180, max(60, len(self.ciphertext)*0.01))
        start_time = time.time()
        loglikelihood = []
        accepted = []
        while(int(time.time()-start_time)<runningtime):
            f2 = self.generate_f(self.cur_f, self.set1, self.set2)
            pf2 = self.Pf(f2)
            pf1 = self.Pf(self.cur_f)

            if self.accept(newscore=pf2, oldscore=pf1):
                accepted.append(True)
                self.cur_f = f2
            else:
                accepted.append(False)

            if self.Pf(self.cur_f) != "not exist":
                loglikelihood.append(self.Pf(self.cur_f))
            else:
                loglikelihood.append(float('nan'))

            if (len(loglikelihood)>max(len(self.ciphertext)*0.01, 500) and np.std(loglikelihood[-500:]) < 0.001):
                break
           
        return loglikelihood[-1], self.cur_f

def decode_content(content, f):
    s = ""
    for c in content:
        s += idx2alpha[f[c]]
    return s

def match_words(content):
    ws = content.replace(".", "").split(" ")
    score = 0
    for w in ws:
        if len(w) > 0 and w in words_dict[w[0]]:
            score += 1
    score = float(score)/len(ws)
    return score

class MCMC_short(MCMC):
    def __init__(self, ciphertext):
        MCMC.__init__(self, ciphertext)
        self.space = max(set(list(ciphertext)), key=list(ciphertext).count)
        self.alphabet_short = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r',
                               's', 't', 'u', 'v', 'w', 'x', 'y', 'z', " ", "."]
        self.alphabet_short.remove(self.space)
        alphabet2 = self.alphabet_short
        random.shuffle(alphabet2)
        self.cur_f = dict(zip(alphabet2, [x for x in range(28) if x != 26]))
        self.cur_f[self.space] = 26

    def Pf(self, code2idx):
        decoded_text = decode_content(self.ciphertext, code2idx)
        score = match_words(decoded_text)
        return score

    def generate_f(self, oldf, set1, set2):
        # set1: "."
        # set2 : " "
        a, b = random.sample(self.alphabet_short, 2)
        f2 = oldf.copy()
        f2[a] = oldf[b]
        f2[b] = oldf[a]
        return f2

class MCMC_B(MCMC):
    def __init__(self, ciphertext, f1=None, f2=None):
        self.alphabet = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r',
                         's', 't', 'u', 'v', 'w', 'x', 'y', 'z', ' ', '.']
        self.idx2alpha = dict(zip(range(28), self.alphabet))
        self.ciphertext_transition = collections.Counter()
        for a in self.alphabet:
            self.ciphertext_transition[a] = collections.Counter()
        for i in range(1, len(ciphertext), 1):  # including /n
            self.ciphertext_transition[ciphertext[i]][ciphertext[i - 1]] += 1
        self.ciphertext = ciphertext

        # Compute the possible region of breakpoint
        self.minbs, self.maxbs, self.leftsets, self.rightsets = breakpoint_range(self.ciphertext)
        self.breakpoint = random.randint(self.minbs, self.maxbs + 1)


        # Initialize ciphering functions
        self.cur_f1 = f1
        self.cur_f2 = f2

        if (self.cur_f1 == None or self.cur_f2 == None):
            alphabet = self.alphabet
            if (self.cur_f1 == None):
                random.shuffle(alphabet)
                self.cur_f1 = dict(zip(alphabet, range(28)))
                self.cur_f1 = self.generate_f(self.cur_f1, self.leftsets[0], self.leftsets[1])
            if (self.cur_f2 == None):
                random.shuffle(alphabet)
                self.cur_f2 = dict(zip(alphabet, range(28)))
                self.cur_f2 = self.generate_f(self.cur_f2, self.rightsets[0], self.rightsets[1])

        self.ciphertext_transition_left = collections.Counter()
        for a in self.alphabet:
            self.ciphertext_transition_left[a] = collections.Counter()
        for i in range(1, self.minbs, 1):  # including /n
            self.ciphertext_transition_left[ciphertext[i]][ciphertext[i - 1]] += 1

        self.ciphertext_transition_right = collections.Counter()
        for a in self.alphabet:
            self.ciphertext_transition_right[a] = collections.Counter()
        for i in range(self.maxbs+1, len(self.ciphertext), 1):  # including /n
            self.ciphertext_transition_right[ciphertext[i]][ciphertext[i - 1]] += 1
        self.b_sigma = (self.maxbs-self.minbs)*0.2

    def refine_breakpoint(self):
        best_breakpoint = self.breakpoint
        best_score = -1e10
        content = self.ciphertext[self.minbs:self.maxbs]
        for b in range(0, self.maxbs-self.minbs, 1):
            decoded = decode_content(content[:b], self.cur_f1) + decode_content(content[b:], self.cur_f2)
            if "." in decoded[:-1] and ". " not in decoded:
                pass
            else:
                score = 0
                ws = decoded.replace(".", "").split(" ")
                for w in ws:
                    if len(w)>0 and w in words_dict[w[0]]:
                        score += 1
                if score > best_score:
                    best_breakpoint = b
                    best_score = score
        self.breakpoint = best_breakpoint+self.minbs

    def Pf(self, code2idx1, code2idx2, breakpoint):
        if breakpoint == len(self.ciphertext):
            return "not exist", "not exist"


        logPf1 = logP[code2idx1[self.ciphertext[0]]]

        for a in self.alphabet:
            for b in self.alphabet:
                if self.ciphertext_transition_left[a][b]!=0 and logPf1!= "not exist":
                    if logM[code2idx1[a], code2idx1[b]] == -float('inf'):
                        logPf1 = "not exist"
                        break
                    else:
                        logPf1 += self.ciphertext_transition_left[a][b] * logM[code2idx1[a], code2idx1[b]]

        if logPf1 != "not exist":
            for idx in range(self.minbs, breakpoint, 1):
                if logM[code2idx1[self.ciphertext[idx]], code2idx1[self.ciphertext[idx - 1]]] == -float('inf') and logPf1!="not exist":
                    logPf1 = "not exist"
                    break
                else:
                    logPf1 += logM[code2idx1[self.ciphertext[idx]], code2idx1[self.ciphertext[idx - 1]]]

        logPf2 = logP[code2idx2[self.ciphertext[breakpoint]]]
        for a in self.alphabet:
            for b in self.alphabet:
                if self.ciphertext_transition_right[a][b]!=0 and logPf2!="not exist":
                    if logM[code2idx2[a], code2idx2[b]] == -float('inf'):
                        logPf2 =  "not exist"
                        return logPf1, logPf2
                    else:
                        logPf2 += self.ciphertext_transition_right[a][b] * logM[code2idx2[a], code2idx2[b]]

        if logPf2 != "not exist":
            for idx in range(breakpoint + 1, self.maxbs, 1):
                if logM[code2idx2[self.ciphertext[idx]], code2idx2[self.ciphertext[idx - 1]]] == -float('inf'):
                    logPf2 = "not exist"
                    return logPf1, logPf2
                else:
                    logPf2 += logM[code2idx2[self.ciphertext[idx]], code2idx2[self.ciphertext[idx - 1]]]
        return logPf1, logPf2

    def decode(self):
        s = ""
        for c in range(self.breakpoint):
            s += self.idx2alpha[self.cur_f1[self.ciphertext[c]]]
        for c in range(self.breakpoint, len(self.ciphertext), 1):
            s += self.idx2alpha[self.cur_f2[self.ciphertext[c]]]
        return s

    def run(self, runningtime=-1):
        if runningtime == -1:
            runningtime = min(90, max(20, len(self.ciphertext)*0.01))

        loglikelihood = []

        start_time = time.time()
        while(time.time()-start_time< runningtime):
            new_f1 = self.generate_f(self.cur_f1, self.leftsets[0], self.leftsets[1])
            new_f2 = self.generate_f(self.cur_f2, self.rightsets[0], self.rightsets[1])
            pfnew_f1, pfnew_f2 = self.Pf(new_f1, new_f2, self.breakpoint)
            pfold_f1, pfold_f2 = self.Pf(self.cur_f1, self.cur_f2, self.breakpoint)

            if self.accept(newscore=pfnew_f1, oldscore=pfold_f1):
                self.cur_f1 = new_f1
            if self.accept(newscore=pfnew_f2, oldscore=pfold_f2):
                self.cur_f2 = new_f2

            new_b = int(np.random.normal(loc=self.breakpoint, scale=self.b_sigma))
            while(new_b<self.minbs or new_b>self.maxbs):
                if random.random() > 0.1:
                    new_b = int(np.random.normal(loc=self.breakpoint, scale=(self.maxbs - self.minbs) * 0.2))
                else:
                    new_b = int((self.minbs + self.maxbs)/2)
            pfnew_f1, pfnew_f2 = self.Pf(self.cur_f1, self.cur_f2, new_b)

            if pfnew_f1 == "not exist" or pfnew_f2 == "not exist":
                pfnew_b = "not exist"
            else:
                pfnew_b = pfnew_f1 * pfnew_f2
            if pfold_f1 == "not exist" or pfold_f2 == "not exist":
                pfold_b = "not exist"
            else:
                pfold_b = pfold_f1 * pfold_f2


            if self.accept(newscore=pfnew_b, oldscore=pfold_b):
                self.breakpoint = new_b
                if(pfnew_b != "not exist"):
                    loglikelihood.append(pfnew_b)
            else:
                if(pfold_b != "not exist"):
                    loglikelihood.append(pfold_b)

            if(len(loglikelihood)>1000 and np.std(loglikelihood[-500:])<0.001):
                break

        return self.decode()


def decode_short(ciphertext):
    numspaces = 0
    best_breakpoint = 0
    l = list(ciphertext)
    for i in range(1, len(ciphertext)-1):
        num = l[:i].count(max(set(l[:i]), key=list(l[:i]).count)) + l[i:].count(max(set(l[i:]), key=list(l[i:]).count))
        if num > numspaces:
            numspaces = num
            best_breakpoint = i
    left, _ = multi_merge(ciphertext[:best_breakpoint], np=30, runningtime1=90, runningtime2=20)
    right, _ = multi_merge(ciphertext[best_breakpoint:], np=30, runningtime1=90, runningtime2=20)
    return left + right


class MCMC_B_short(MCMC_B):
    def __init__(self, ciphertext, f1=None, f2=None):
        MCMC_B.__init__(self, ciphertext, f1, f2)
        self.b_sigma = 1


    def Pf(self, code2idx1, code2idx2, breakpoint):
        if breakpoint == len(self.ciphertext):
            return "not exist", "not exist"
        decoded_text1 = decode_content(self.ciphertext[:breakpoint], code2idx1)
        decoded_text2 = decode_content(self.ciphertext[breakpoint:], code2idx2)
        return match_words(decoded_text1), match_words(decoded_text2)

    def generate_f(self, oldf, set1, set2):
        # set1: "."
        # set2 : " "
        a, b = random.sample(self.alphabet, 2)
        f2 = oldf.copy()
        f2[a] = oldf[b]
        f2[b] = oldf[a]

        return f2
        
def run(args):
    ciphertext, seed, runningtime = args
    random.seed(seed)
    mcmc = MCMC(ciphertext=ciphertext)
    loglikelihood, cur_f = mcmc.run(runningtime=runningtime)
    return loglikelihood, cur_f
        
def multi_merge(ciphertext, np=10, runningtime1=-1, runningtime2=-1): # 270s

    # 180s
    p = Pool(processes=np)
    data = p.map(run, zip([ciphertext]*np, [time.time()*random.random() for i in range(np)], [runningtime1]*np))
    p.close()
    
    best_loglikelihood = -float('inf')
    best_f = None
    for i in data:
        if(i[0]==i[0] and i[0]>best_loglikelihood):
            best_loglikelihood = i[0]
            best_f = i[1]

    plaintext = decode_content(ciphertext, best_f)

    if len(ciphertext)<SHORT_TEXT:
        short_mcmc = MCMC_short(ciphertext=ciphertext)
        short_mcmc.cur_f = best_f.copy()
        short_mcmc.run(runningtime=runningtime2) # 90s
        short_plaintext = short_mcmc.decode()
        if(match_words(short_plaintext)>match_words(plaintext)):
            return short_plaintext, short_mcmc.cur_f
    return plaintext, best_f

def breakpoint_range(content):
    l = 0
    r = len(content)
    # [minb, maxb)
    # determining the maximum x such that ciphertext[:x] valid
    while (l <= r):
        m = int(l + (r - l) / 2)
        a, b = checkvalid(content[m:])
        if (len(a) > 0 and len(b) > 0):
            r = m - 1
        else:
            l = m + 1
    minbs = l
    leftsets = checkvalid(content[:minbs])

    l = 0
    r = len(content)
    # [minb, maxb)
    # determining the minimum x such that ciphertext[x:] valid
    while (l <= r):
        m = int(l + (r - l) / 2)
        a, b = checkvalid(content[:m])
        if (len(a) > 0 and len(b) > 0):
            l = m + 1
        else:
            r = m - 1
    maxbs = r
    rightsets = checkvalid(content[maxbs:])

    return minbs, maxbs, leftsets, rightsets


def decode(ciphertext, has_breakpoint):
    if not has_breakpoint:
        # 270s
        try:
            plaintext, _ = multi_merge(ciphertext, np=30)
        except:
            plaintext, _ = multi_merge(ciphertext, np=5)
        plaintext = refine(plaintext, words)

    else:
        minb, maxb, leftsets, rightsets = breakpoint_range(ciphertext)  # for small data, minb=0, maxb=len(str)

        if minb==0 or maxb==len(ciphertext):
            plaintext = decode_short(ciphertext) # 270s * 2

        else:
            lefttext, single_f1 = multi_merge(ciphertext[:minb]) # 270s
            righttext, single_f2 = multi_merge(ciphertext[maxb:]) # 270s

            try:
                mcmc = MCMC_B(ciphertext=ciphertext, f1=single_f1, f2=single_f2)
                _ = mcmc.run() # 90s
                mcmc.refine_breakpoint()
                plaintext = mcmc.decode()
                plaintext = refine(plaintext[:mcmc.breakpoint], words) + refine(plaintext[mcmc.breakpoint:], words)

                try:
                    if len(ciphertext) < SHORT_TEXT:
                        short_mcmc = MCMC_B_short(ciphertext=ciphertext, f1=single_f1, f2=single_f2)
                        checkresult = short_mcmc.decode()
                        if max(set(final_mcmc.alphabet), key=list(checkresult).count) == " ":
                            _ = mcmc.run(runningtime=20) # 20s
                            short_mcmc.refine_breakpoint()
                            short_plaintext = short_mcmc.decode()
                            short_plaintext = refine(short_plaintext[:short_mcmc.breakpoint], words) + refine(short_plaintext[short_mcmc.breakpoint:], words)
                        else:
                            short_plaintext = decode_short(ciphertext)

                        if match_words(short_plaintext) > match_words(plaintext):
                            return short_plaintext
                except:
                    traceback.print_exc()
                    pass
            except:
                plaintext = refine(lefttext, words) + ciphertext[minb:maxb] + refine(righttext, words)
                traceback.print_exc()

    return plaintext