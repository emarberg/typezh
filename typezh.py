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


CANTONESE_LANGUAGE = 0
CHINESE_TRADITIONAL_LANGUAGE = 1
CHINESE_SIMPLIFIED_LANGUAGE = 2

TEXT_TO_TEXT_MODE = 0
SOUND_TO_TEXT_MODE = 1
MEANING_TO_TEXT_MODE = 2

# zh-to-zh
TRADITIONAL_MODE = 0
SIMPLIFIED_MODE = 1

# sound-to-zh
INVISIBLE_TRADITIONAL_MODE = 3
INVISIBLE_SIMPLIFIED_MODE = 4

# sequential-text-to-text
# TODO

# sequential-sound-to-text
# TODO 

# meaning-to-zh
# TODO

# meaning-to-canto
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
    SENTENCES_FILE = 'sentences/sentences_yue.csv'

    def __init__(self, profile, language, mode, filtered=True, custom_input=None):
        self.profile = profile
        self.language = language
        self.mode = mode
        self.char_filter_on = filtered

        if self.char_filter_on:
            assert custom_input is None
        
        self.set_directory()
        self.new_translations = []
        self.index = None if custom_input is None else 0
        self.setup_profile(custom_input)
        self.read_sentences(custom_input)

        self.quit = False
        self.temp_sound = ''

    def speak(self, s, temp=True):
        try:
            voice = '--voice zh-HK-HiuGaaiNeural' if self.in_cantonese_mode() else ''
            folder = 'yue' if self.in_cantonese_mode() else 'zh'
            if temp:
                if self.temp_sound != s:
                    systemcall('edge-tts %s --text "%s" --write-media sounds/%s/temp.mp3 >/dev/null 2>&1; afplay sounds/%s/temp.mp3 >/dev/null 2>&1' % (voice, s, folder, folder))
                    self.temp_sound = s
                else:
                    system('afplay sounds/%s/temp.mp3 >/dev/null 2>&1' % folder)
            else:
                file_name = "sounds/%s/%s.mp3" % (folder, s)
                file_path = Path(file_name)

                if not file_path.exists():
                    systemcall('edge-tts %s --text "%s" --write-media %s >/dev/null 2>&1; afplay %s >/dev/null 2>&1' % (voice, s, file_name, file_name))
                else:
                    system('afplay %s >/dev/null 2>&1' % file_name)
        except SystemCallError:
            if self.in_cantonese_mode():
                system('say -v Meijia ' + s)
            else:
                system('say -v Sinji ' + s)

    def has_unallowed_chars(self, s):
        chars = set(s) - set(self.PUNCTUATION)
        if self.char_filter_on:
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

        if self.in_traditional_mode() and not is_traditional(s):
            return False
        if self.in_simplified_mode() and not is_simplified(s):
            return False
        return True

    def in_sequential_mode(self):
        return self.index is not None

    def in_cantonese_mode(self):
        return self.language == CANTONESE_LANGUAGE

    def in_traditional_mode(self):
        return self.mode in [TRADITIONAL_MODE, INVISIBLE_TRADITIONAL_MODE]

    def in_simplified_mode(self):
        return self.mode in [SIMPLIFIED_MODE, INVISIBLE_SIMPLIFIED_MODE]

    def set_directory(self):
        ans = './profiles/' + self.profile + '/'
        
        if self.language == CANTONESE_LANGUAGE:
            ans += 'yue'
        elif self.language == CHINESE_TRADITIONAL_LANGUAGE:
            ans += 'zh-trad'
        elif self.language == CHINESE_SIMPLIFIED_LANGUAGE:
            ans += 'zh-simp'
        else:
            raise Exception

        ans += '/'

        if self.mode == TEXT_TO_TEXT_MODE:
            ans += 'text-to-text'
        elif self.mode == SOUND_TO_TEXT_MODE:
            ans += 'sound-to-text'
        elif self.mode == MEANING_TO_TEXT_MODE:
            ans += 'meaning-to-text'
        else:
            raise Exception

        self.directory = ans

    def setup_profile(self, custom_input):
        Path(self.directory).mkdir(parents=True, exist_ok=True)
        
        self.charfile = self.directory + '/characters.txt'
        Path(self.charfile).touch()
        self.setup_char_filter(custom_input)

        self.review_stats_file = self.directory + '/reviews.csv'
        Path(self.review_stats_file).touch()
        self.setup_review_stats()

        self.coverage_stats_file = self.directory + '/coverage.csv'
        Path(self.coverage_stats_file).touch()
        self.setup_coverage_stats()

    def setup_review_stats(self):
        self.reviews = {int_today(): 0}
        with open(self.review_stats_file) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                day, count = list(map(int, row))
                self.reviews[day] = self.reviews.get(day, 0) + count

    def setup_coverage_stats(self):
        self.coverage = {}
        with open(self.coverage_stats_file) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                char, count = row[0], int(row[1])
                self.coverage[char] = count

    def setup_char_filter(self, custom_input):
        with open(self.charfile) as file:
            file_content = set(file.read().strip())
            self.char_filter = {c for c in file_content if is_hanzi(c)}

    def update_char_filter(self):
        if not self.in_sequential_mode():
            filter_off = not self.char_filter_on
            
            clear_screen()
            if len(self.zh_sentences) == 0:
                print()
                print('right now there are no sentences to review')
            if filter_off:
                print()
                raise KeyboardInterrupt

            self.char_filter_on = True
            self.update_sentences()
            a = len(self.zh_sentences)
            b = len(self.char_filter)

            print()
            if filter_off:
                print('character filter is currently off.')
                print()
            print('reviewable characters with filter:', b)
            print(' reviewable sentences with filter:', a) 
            
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
                bb = len(self.char_filter)
                
                self.update_sentences()
                aa = len(self.zh_sentences)
                
                if filter_off:
                    self.char_filter_on = False
                    self.update_sentences()
                
                print()
                print('reviewable characters with filter:', b, '->', bb)
                print(' reviewable sentences with filter:', a, '->', aa) 
                print()
                input('')

    def sentence_files(self):
        yield self.SENTENCES_FILE
        # yield "./profiles/" + self.profile + "/sentences_zh.csv"

    def translation_files(self):
        yield self.directory + "/translations.csv"

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

    def save(self):
        file = self.directory + "/translations.csv"
        Path(file).touch()
        with open(file, 'a', newline='\n') as csvfile:
            writer = csv.writer(csvfile)
            for zh, eng in self.new_translations:
                if eng:
                    writer.writerow([eng, zh])

        with open(self.review_stats_file, 'w', newline='\n') as csvfile:
            writer = csv.writer(csvfile)
            for day in sorted(self.reviews):
                count = self.reviews[day]
                writer.writerow([day, count])

        with open(self.coverage_stats_file, 'w', newline='\n') as csvfile:
            writer = csv.writer(csvfile)
            for char in sorted(self.coverage):
                count = self.coverage[char]
                writer.writerow([char, count])

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
        # clear_screen()
        print()

    def get_sentence(self):
        if (self.index is None and len(self.zh_sentences) == 0) or (self.index is not None and self.index >= len(self.zh_sentences)):
            self.update_char_filter()
            return self.get_sentence()
        elif self.index is None:
            return random.choice(self.zh_sentences)
        else:
            self.index += 1
            return self.zh_sentences[self.index - 1]

    def get_translation(self, sentence):
        if sentence in self.zh_dict:
            return self.zh_dict[sentence]

    def add_translation(self, sentence):
        print('add translation (or type \'lookup\'):')
        print()      
        s = input('  ').strip()
        if s == '':
            return
        if s == 'lookup':
            sl ='yue' if self.in_cantonese_mode() else 'zh'
            translate_with_google(sentence, sl=sl, tl='en')
            self.print_sentence(sentence, False)
            print('add translation (or press enter to skip):')
            print()  
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
        self.print_sentence(sentence, False)
        self.speak(sentence, temp=False)
        pyperclip.copy(sentence)
        translation = self.get_translation(sentence)
        if translation is None:
            self.add_translation(sentence)
        else:
            print(translation)
            print()
            s = input('  ')

        today = int_today()
        self.reviews[today] = self.reviews.get(today, 0) + 1
        
        for c in set(sentence):
            if is_hanzi(c):
                self.coverage[c] = self.coverage.get(c, 0) + 1
        
    def matches(self, sentence, received):
        a = tuple(s for s in sentence if s not in self.PUNCTUATION)
        b = tuple(s for s in received if s not in self.PUNCTUATION)
        return a == b

    def is_invisible(self):
        return self.mode in [INVISIBLE_TRADITIONAL_MODE, INVISIBLE_SIMPLIFIED_MODE]

    def get_stats_today(self):
        return self.reviews.get(int_today(), 0)

    def get_stats_week(self):
        a = int_today()
        ans = 0
        for i in range(7):
            ans += self.reviews.get(a - i, 0)
        return ans

    def get_stats_total(self):
        ans = 0
        for dates in self.reviews:
            ans += self.reviews[dates]
        return ans

    def mode_str(self):
        if self.in_cantonese_mode():
            return '[粵]'
        elif self.in_simplified_mode():
            return '[简体]'
        elif self.in_traditional_mode():
            return '[繁體]'
        else:
            raise Exception

    def print_sentence(self, sentence, invisible, base=''):
        if invisible:
            sentence = sentence[:len(base)] + ''.join(['一' if is_hanzi(c) else c for c in sentence[len(base):]])

        if self.in_sequential_mode():
            rnum_str = 'sentence # %s' % self.index
        else:
            a = self.get_stats_today() + 1 
            b = self.get_stats_week()
            b = round((b + 1) / 7.0, 2)
            # rnum_str = 'reviews: %s (today), %s (weekly average)' % (a, b)

        clear_screen()
        print()
        print(self.mode_str(), 'reviewable:', len(self.zh_sentences), '| today (week):', a, '(%s)' % b)
        print()
        print(' ', sentence)
        print()

    def extend_match(self, sentence, base, s):
        ell = len(base)
        end = ell
        
        q1 = [a for a in s if a not in self.PUNCTUATION]
        q2 = [(i + 1, sentence[i]) for i in range(ell, len(sentence)) if sentence[i] not in self.PUNCTUATION]

        while q1 and q2:
            i, a = q2[0]
            b = q1[0]

            invisible_exception = self.is_invisible() and {a, b}.issubset({'她', '他'})
            if a == b or invisible_exception:
                end = i
                q1 = q1[1:]
                q2 = q2[1:]
            else:
                break

        if len(q1) == 0 and len(q2) == 0:
            return sentence
        else:
            return sentence[:end]

    def jump(self, sentence):
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

    def review(self):
        aloud = self.is_invisible()
        sentence = self.get_sentence()

        base = ''
        while True:
            pyperclip.copy(sentence[len(base):len(base) + 1])
            self.print_sentence(sentence, self.is_invisible(), base)
            
            if aloud:
                self.speak(sentence[len(base):])
            
            s = input('  ' + base)

            if s == 'q' or s == 'quit':
                self.quit = True
                break

            if s == 'jump':
                self.jump(sentence)
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
                        
            base = self.extend_match(sentence, base, s)

            if self.matches(sentence, base):
                self.update_translations(sentence)
                break
            else:
                aloud = True


def main():
    manager = Manager('default', CANTONESE_LANGUAGE, TEXT_TO_TEXT_MODE)#, 'mindiworldnews/20260324.txt')
    manager.run()


if __name__ == '__main__':
    main()