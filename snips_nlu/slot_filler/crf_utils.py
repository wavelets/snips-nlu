from enum import Enum, unique

from snips_nlu.constants import TEXT, SLOT_NAME
from snips_nlu.tokenization import tokenize, Token

BEGINNING_PREFIX = u'B-'
INSIDE_PREFIX = u'I-'
LAST_PREFIX = u'L-'
UNIT_PREFIX = u'U-'
OUTSIDE = u'O'

RANGE = u"range"
TAGS = u"tags"
TOKENS = u"tokens"


@unique
class TaggingScheme(Enum):
    IO = 0
    BIO = 1
    BILOU = 2


def tag_name_to_slot_name(tag):
    return tag[2:]


def start_of_io_slot(tags, i):
    if i == 0:
        return tags[i] != OUTSIDE
    if tags[i] == OUTSIDE:
        return False
    return tags[i - 1] == OUTSIDE


def end_of_io_slot(tags, i):
    if i + 1 == len(tags):
        return tags[i] != OUTSIDE
    if tags[i] == OUTSIDE:
        return False
    return tags[i + 1] == OUTSIDE


def start_of_bio_slot(tags, i):
    if i == 0:
        return tags[i] != OUTSIDE
    if tags[i] == OUTSIDE:
        return False
    if tags[i].startswith(BEGINNING_PREFIX):
        return True
    if tags[i - 1] != OUTSIDE:
        return False
    return True


def end_of_bio_slot(tags, i):
    if i + 1 == len(tags):
        return tags[i] != OUTSIDE
    if tags[i] == OUTSIDE:
        return False
    if tags[i + 1].startswith(INSIDE_PREFIX):
        return False
    return True


def start_of_bilou_slot(tags, i):
    if i == 0:
        return tags[i] != OUTSIDE
    if tags[i] == OUTSIDE:
        return False
    if tags[i].startswith(BEGINNING_PREFIX):
        return True
    if tags[i].startswith(UNIT_PREFIX):
        return True
    if tags[i - 1].startswith(UNIT_PREFIX):
        return True
    if tags[i - 1].startswith(LAST_PREFIX):
        return True
    if tags[i - 1] != OUTSIDE:
        return False
    return True


def end_of_bilou_slot(tags, i):
    if i + 1 == len(tags):
        return tags[i] != OUTSIDE
    if tags[i] == OUTSIDE:
        return False
    if tags[i + 1] == OUTSIDE:
        return True
    if tags[i].startswith(LAST_PREFIX):
        return True
    if tags[i].startswith(UNIT_PREFIX):
        return True
    if tags[i + 1].startswith(BEGINNING_PREFIX):
        return True
    if tags[i + 1].startswith(UNIT_PREFIX):
        return True
    return False


def _tags_to_slots(tags, tokens, is_start_of_slot, is_end_of_slot):
    slots = []
    current_slot_start = 0
    for i, tag in enumerate(tags):
        if is_start_of_slot(tags, i):
            current_slot_start = i
        if is_end_of_slot(tags, i):
            slots.append({
                RANGE: (tokens[current_slot_start].start, tokens[i].end),
                SLOT_NAME: tag_name_to_slot_name(tag)
            })
            current_slot_start = i
    return slots


def tags_to_slots(tokens, tags, tagging_scheme):
    if tagging_scheme == TaggingScheme.IO:
        return _tags_to_slots(tags, tokens, start_of_io_slot, end_of_io_slot)
    elif tagging_scheme == TaggingScheme.BIO:
        return _tags_to_slots(tags, tokens, start_of_bio_slot, end_of_bio_slot)
    elif tagging_scheme == TaggingScheme.BILOU:
        return _tags_to_slots(tags, tokens, start_of_bilou_slot,
                              end_of_bilou_slot)
    else:
        raise ValueError("Unknown tagging scheme %s" % tagging_scheme)


def positive_tagging(tagging_scheme, slot_name, slot_size):
    if tagging_scheme == TaggingScheme.IO:
        tags = [INSIDE_PREFIX + slot_name for _ in xrange(slot_size)]
    elif tagging_scheme == TaggingScheme.BIO:
        tags = [BEGINNING_PREFIX + slot_name]
        tags += [INSIDE_PREFIX + slot_name for _ in xrange(1, slot_size)]
    elif tagging_scheme == TaggingScheme.BILOU:
        if slot_size == 1:
            tags = [UNIT_PREFIX + slot_name]
        else:
            tags = [BEGINNING_PREFIX + slot_name]
            tags += [INSIDE_PREFIX + slot_name
                     for _ in xrange(1, slot_size - 1)]
            tags.append(LAST_PREFIX + slot_name)
    else:
        raise ValueError("Invalid tagging scheme %s" % tagging_scheme)
    return tags


def negative_tagging(size):
    return [OUTSIDE for _ in xrange(size)]


def utterance_to_sample(query_data, tagging_scheme):
    tokens, tags = [], []
    current_length = 0
    for i, chunk in enumerate(query_data):
        chunk_tokens = tokenize(chunk[TEXT])
        tokens += [Token(t.value, current_length + t.start,
                         current_length + t.end) for t in chunk_tokens]
        current_length += len(chunk[TEXT])
        if SLOT_NAME not in chunk:
            tags += negative_tagging(len(chunk_tokens))
        else:
            tags += positive_tagging(tagging_scheme, chunk[SLOT_NAME],
                                     len(chunk_tokens))
    return {TOKENS: tokens, TAGS: tags}


def get_scheme_prefix(index, indexes, tagging_scheme):
    if tagging_scheme == TaggingScheme.IO:
        return INSIDE_PREFIX
    elif tagging_scheme == TaggingScheme.BIO:
        if index == indexes[0]:
            return BEGINNING_PREFIX
        else:
            return INSIDE_PREFIX
    elif tagging_scheme == TaggingScheme.BILOU:
        if len(indexes) == 1:
            return UNIT_PREFIX
        if index == indexes[0]:
            return BEGINNING_PREFIX
        if index == indexes[-1]:
            return LAST_PREFIX
        else:
            return INSIDE_PREFIX
    else:
        raise ValueError("Invalid tagging scheme %s" % tagging_scheme)