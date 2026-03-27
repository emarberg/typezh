import csv 
import os
from os import system
from pathlib import Path
from collections import OrderedDict, Counter
import pyperclip
import random
import readline
from datetime import datetime, timezone

import webbrowser
import urllib.parse

from simplifier import (
    simplify, 
    is_simplified, 
    is_traditional, 
    TRADSET, 
    SIMPSET, 
    BOTHSET
)

# zh-to-zh
TRADITIONAL_MODE = 0
SIMPLIFIED_MODE = 1
BOTH_MODE = 2

# sound-to-zh
INVISIBLE_TRADITIONAL_MODE = 3
INVISIBLE_SIMPLIFIED_MODE = 4
INVISIBLE_BOTH_MODE = 5

# sequential-text-to-text
# TODO

# sequential-sound-to-text
# TODO 

# meaning-to-zh
# TODO

# meaning-to-yue
# TODO




def first_ord():
    return ord('㗎')


def last_ord():
    return ord('龟')


def is_hanzi(c):
    return first_ord() <= ord(c) <= last_ord()


def int_today():
    aware_utc_now = datetime.now(timezone.utc)
    utc_timestamp = aware_utc_now.timestamp()
    return int(utc_timestamp / 86400)


def clear_screen():
    # Use 'cls' for Windows, 'clear' for POSIX systems (Linux/macOS)
    os.system('cls' if os.name == 'nt' else 'clear')


def translate_with_google(text, sl='auto', tl='en'):
    """
    Opens Google Translate in the browser with input text.
    sl: source language (default auto)
    tl: target language (default english)
    """
    # URL encode the text to handle spaces and special characters
    encoded_text = urllib.parse.quote(text)
    
    # Construct the URL
    url = f"https://translate.google.com/?sl={sl}&tl={tl}&text={encoded_text}&op=translate"
    
    # Open in default web browser
    webbrowser.open(url)


class SystemCallError(Exception):
    pass


def systemcall(command):
    exit_code = system(command)
    if exit_code != 0:
        raise SystemCallError


class Manager:

    PUNCTUATION = '\'-#`•／‘」}{+~；。*@﹐°「？→(─—‧_﹣《<]./¨=\\\'！&』["!)’－₣>;$・”％“》〉〈,:、）»﹖?﹗＂%，．·^|：～（«\\\\–『\' 【】'
    SENTENCES_FILE = 'sentences/sentences_zh.csv'
    TRANSLATIONS_FILE = 'sentences/translations_zh.csv'

    def __init__(self, profile, mode, custom_input=None):
        self.mode = mode
        self.muted = False
        self.profile = profile
        self.new_translations = []
        
        self.stats = {}
        self.stats[self.mode] = {int_today(): 0}
        
        self.index = None if custom_input is None else 0
        self.setup_profile(custom_input)
        self.read_sentences(custom_input)

        self.quit = False
        self.temp_sound = ''

    def speak(self, s, temp=True):
        if not self.muted:
            try:
                if temp:
                    if self.temp_sound != s:
                        systemcall('edge-tts --text "%s" --write-media sounds/temp.mp3 >/dev/null 2>&1; afplay sounds/temp.mp3 >/dev/null 2>&1' % s)
                        self.temp_sound = s
                    else:
                        system('afplay sounds/temp.mp3 >/dev/null 2>&1')
                else:
                    file_name = "sounds/%s.mp3" % s
                    file_path = Path(file_name)

                    if not file_path.exists():
                        systemcall('edge-tts --text "%s" --write-media %s >/dev/null 2>&1; afplay %s >/dev/null 2>&1' % (s, file_name, file_name))
                    else:
                        system('afplay %s >/dev/null 2>&1' % file_name)
            except SystemCallError:
                system('say -v Meijia ' + s)

    def has_unallowed_chars(self, s):
        chars = set(s) - set(self.PUNCTUATION)
        if self.char_filter:
            zh_chars = {c for c in chars if is_hanzi(c)}
            if len(zh_chars - self.char_filter) > 0:
                return True
        return False

    def is_valid_sentence(self, s):
        if not any(is_hanzi(c) for c in s):
            return False

        chars = set(s) - set(self.PUNCTUATION)

        if any(ord('a') <= ord(c) <= ord('z') or ord('A') <= ord(c) <= ord('Z') or ord(c) > last_ord() for c in chars):
            return False

        if self.ịn_traditional_mode() and not is_traditional(s):
            return False
        if self.in_simplifed_mode() and not is_simplified(s):
            return False
        return True

    def in_sequential_mode(self):
        return self.index is not None

    def in_traditional_mode(self):
        return self.mode in [TRADITIONAL_MODE, INVISIBLE_TRADITIONAL_MODE]

    def in_simplified_mode(self):
        return self.mode in [SIMPLIFIED_MODE, INVISIBLE_SIMPLIFIED_MODE]

    def setup_profile(self, custom_input):
        Path('./profiles/' + self.profile).mkdir(parents=True, exist_ok=True)
        
        if custom_input is not None:
            self.char_filter = None
        else:
            self.charfile = './profiles/' + self.profile + '/characters.txt'
            Path(self.charfile).touch()
            with open(self.charfile) as file:
                file_content = set(file.read().strip())
                if '*' in file_content or not file_content:
                    self.char_filter = None
                else:
                    self.char_filter = {c for c in file_content if is_hanzi(c)}

        self.statsfile = './profiles/' + self.profile + '/statistics.csv'
        Path(self.statsfile).touch()
        with open(self.statsfile) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                mode, day, count = list(map(int, row))
                if mode not in self.stats:
                    self.stats[mode] = {}
                if day not in self.stats[mode]:
                    self.stats[mode][day] = 0
                self.stats[mode][day] = count

    def update_char_filter(self):
        if self.char_filter is not None:
            a = len(self.zh_sentences)
            b = len(self.char_filter)
            clear_screen()
            print()
            print('reviewable characters:', b)
            print('reviewable sentences :', a) 
            delta = 20
            addable = sorted([c for c in self.counter if c not in self.char_filter], key=lambda x: -self.counter[x])
            addable = ''.join(addable[:delta])
            pyperclip.copy(addable)
            print()
            print('next %s most common characters:' % delta)
            print()
            print(' ', addable)
            print()
            print('enter additional characters to review:')
            print()
            s = input('  ')
            s = {c for c in s if is_hanzi(c)} - self.char_filter
            if s:
                self.char_filter |= s
                self.update_sentences()
                print()
                print('reviewable characters:', b, '->', len(self.char_filter))
                print('reviewable sentences :', a, '->', len(self.zh_sentences)) 
                print()
                input('')

    def sentence_files(self):
        yield self.SENTENCES_FILE
        yield "./profiles/" + self.profile + "/sentences_zh.csv"

    def translation_files(self):
        yield self.TRANSLATIONS_FILE
        yield "./profiles/" + self.profile + "/translations_zh.csv"

    def update_sentences(self):
        self.zh_sentences = [s for s in self.all_sentences if not self.has_unallowed_chars(s)]
        
    def read_sentences(self, custom_input):
        self.zh_dict = {}
        self.all_sentences = set()

        for file in self.translation_files():
            if not Path(file).exists():
                continue
            with open(file, newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    eng, zh = row
                    self.zh_dict[zh] = eng
                    
        if custom_input is not None:
            with open(custom_input) as file:
                lines = file.read().split('\n')
                lines = [l.strip() for l in lines]
                self.zh_sentences = [l for l in lines if l]

        else:
            for file in self.sentence_files():
                if not Path(file).exists():
                    continue
                with open(file, newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        zh = row[0]
                        if self.is_valid_sentence(zh):
                            self.all_sentences.add(zh)
            
            self.counter = Counter([c for s in self.all_sentences for c in s if is_hanzi(c)])
            self.update_sentences()

        #for zh in self.zh_sentences:
        #    print(zh)
        #    print()
        # print()
        # print(self.char_filter)
        # input('')
        # for zh, eng in self.zh_dict.items():
        #     if eng:
        #         print(zh)
        #         print(eng)
        #         print()
        #input('')

    def save(self):
        file = "./profiles/" + self.profile + "/translations_zh.csv"
        Path(file).touch()
        with open(file, 'a', newline='\n') as csvfile:
            writer = csv.writer(csvfile)
            for zh, eng in self.new_translations:
                if eng:
                    writer.writerow([eng, zh])

        with open(self.statsfile, 'w', newline='\n') as csvfile:
            writer = csv.writer(csvfile)
            for mode in sorted(self.stats):
                for day in sorted(self.stats[mode]):
                    count = self.stats[mode][day]
                    writer.writerow([mode, day, count])

        if self.char_filter is not None:
            with open(self.charfile, 'w', newline='\n') as file:
                chars = sorted(self.char_filter, key=lambda x: -self.counter[x])
                delta = 18
                for i in range(0, len(chars), delta):
                    file.write(''.join(chars[i:i + delta]) + '\n')

    def run(self):
        self.new_translations = []
        while not self.quit:
            try:
                self.review()
            except KeyboardInterrupt:
                self.quit = True
        self.save()
        clear_screen()
        print()

    def get_sentence(self):
        if (self.index is None and len(self.zh_sentences) == 0) or (self.index is not None and self.index >= len(self.zh_sentences)):
            print()
            print('(There are no sentences to review.)')
            raise KeyboardInterrupt
        elif self.index is None:
            return random.choice(self.zh_sentences)
        else:
            self.index += 1
            return self.zh_sentences[self.index - 1]

    def get_translation(self, sentence):
        if sentence in self.zh_dict:
            return self.zh_dict[sentence]

    def add_translation(self, sentence):
        print()
        print('add translation / press enter to use Google')
        print()      
        s = input('  ').strip()
        if s == 'skip':
            return
        if s == '':
            translate_with_google(sentence, sl='zh', tl='en')
            s = input('  ').strip()
        #if s:
        #    print()
        #    confirm = input('press enter to add or any key to skip: ')
        #    if confirm != '':
        #        s = ''
        if s:
            self.zh_dict[sentence] = s
            self.new_translations.append((sentence, s))

    def update_translations(self, sentence):
        self.speak(sentence, temp=False)
        pyperclip.copy(sentence)
        translation = self.get_translation(sentence)
        if translation is None:
            self.add_translation(sentence)
        else:
            print()
            print(translation)
            print()
            s = input('  ')

        today = int_today()
        self.stats[self.mode][today] = self.stats[self.mode].get(today, 0) + 1
        
    def matches(self, sentence, received):
        a = tuple(s for s in sentence if s not in self.PUNCTUATION)
        b = tuple(s for s in received if s not in self.PUNCTUATION)
        return a == b

    def is_invisible(self):
        return self.mode in [INVISIBLE_TRADITIONAL_MODE, INVISIBLE_BOTH_MODE, INVISIBLE_SIMPLIFIED_MODE]

    def print_sentence(self, sentence, invisible):
        if invisible:
            sentence = ''.join(['一' if is_hanzi(c) else c for c in sentence])

        if self.in_sequential_mode():
            rnum_str = '(%s) of (%s)' % (self.index, len(self.zh_sentences))
        else:
            rnum = self.stats[self.mode].get(int_today(), 0)
            rnum_str = '(%s)' % (rnum + 1)

        clear_screen()
        print()
        print('sentence', rnum_str)
        print()
        print(' ', sentence)
        print()

    def extend_match(self, sentence, base, s):
        ell = len(base)
        for i in range(ell, len(s)):
            if i >= len(sentence):
                break
            a, b = s[i], sentence[i]

            invisible_exception = self.is_invisible() and {a, b}.issubset({'她', '他'})
            
            if (a == b) or (a in self.PUNCTUATION and b in self.PUNCTUATION) or invisible_exception:
                base += b
            else:
                break
        return base

    def review(self):
        aloud = self.is_invisible()
        sentence = self.get_sentence()

        base = ''
        while True:
            pyperclip.copy(sentence[len(base):len(base) + 1])
            self.print_sentence(sentence, self.is_invisible())
            print(' ', base, end='')

            if aloud:
                self.speak(sentence[len(base):])
            
            s = input()

            if s == 'q' or s == 'quit':
                self.quit = True
                break

            if s == 'jump':
                if self.in_sequential_mode():
                    clear_screen()
                    print()
                    print('translated document:')
                    while True:
                        translate = self.get_translation(sentence)
                        if translate is None:
                            break
                        print()
                        print(' ', sentence)
                        print()
                        print(' ', translate)
                        print()
                        input('(press enter to continue)')
                        sentence = self.get_sentence()
                aloud = False
                continue
            
            if s == 'reveal':
                if self.is_invisible():
                    self.print_sentence(sentence, False)
                    self.speak(sentence, temp=False)
                    pyperclip.copy(sentence)
                    input('(press enter to continue)')
                    break
                else:
                    aloud = False
                    continue

            if s == 'chars':
                if self.char_filter is None:
                    aloud = False
                    continue
                else:
                    self.update_char_filter()
                    break

            if s == 'skip':
                break
            
            if s == '':
                aloud = True
                continue
                        
            s = base + s
            base = self.extend_match(sentence, base, s)

            if self.matches(sentence, s):
                self.update_translations(sentence)
                break
            else:
                aloud = True


def main():
    manager = Manager('default', TRADITIONAL_MODE, 'mindiworldnews/20260324.txt')
    manager.run()


if __name__ == '__main__':
    main()