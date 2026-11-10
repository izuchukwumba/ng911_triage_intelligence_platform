from ntip.parser.text import clause_around, find_all, last_words, phrase_pattern, sentence_around


class TestPhrasePattern:
    def test_matches_on_word_boundaries_only(self) -> None:
        pattern = phrase_pattern(["od", "hit"])
        assert find_all(pattern, "There is blood on the white wall") == []
        assert [m.text for m in find_all(pattern, "Possible OD. He was hit.")] == ["OD", "hit"]

    def test_prefers_the_longest_phrase(self) -> None:
        pattern = phrase_pattern(["breathing", "not breathing"])
        [match] = find_all(pattern, "He is not breathing")
        assert match.text == "not breathing"

    def test_tolerates_extra_whitespace_and_curly_apostrophes(self) -> None:
        pattern = phrase_pattern(["isn't breathing"])
        assert find_all(pattern, "she isn’t   breathing")[0].text == "isn’t   breathing"

    def test_reports_offsets_into_the_original_text(self) -> None:
        text = "Help! He is NOT BREATHING."
        [match] = find_all(phrase_pattern(["not breathing"]), text)
        assert text[match.start : match.end] == "NOT BREATHING"

    def test_empty_phrase_list_matches_nothing(self) -> None:
        assert find_all(phrase_pattern([]), "anything") == []


class TestSegments:
    def test_clause_stops_at_contrastive_conjunctions(self) -> None:
        text = "He was not breathing earlier but is now. Come quickly."
        start = text.index("not breathing")
        clause = clause_around(text, start, start + len("not breathing"))
        assert text[clause.start : clause.end].strip() == "He was not breathing earlier"

    def test_sentence_spans_conjunctions(self) -> None:
        text = "First. He was hurt but is fine now. Last."
        start = text.index("hurt")
        sentence = sentence_around(text, start, start + 4)
        assert text[sentence.start : sentence.end].strip() == "He was hurt but is fine now"

    def test_last_words(self) -> None:
        assert last_words("I looked and there was NO", 3) == "there was no"
