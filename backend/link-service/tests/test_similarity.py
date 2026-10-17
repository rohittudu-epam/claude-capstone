import pytest

from link_service.similarity import (
    BODY_CHARS,
    TITLE_WEIGHT,
    explain,
    keyword_weights,
    similarity,
    tokenize,
)


class TestTokenize:
    def test_lowercases_and_splits_on_punctuation(self):
        assert tokenize("Kubernetes, Docker/Compose; CI-CD!") == ["kubernetes", "docker", "compose"]

    def test_drops_stopwords_short_tokens_and_numbers(self):
        assert tokenize("the cat is on 2024 and an ox") == ["cat"]

    def test_underscores_split_words(self):
        assert tokenize("snake_case_name") == ["snake", "case", "name"]

    def test_keeps_non_ascii_letters(self):
        assert tokenize("Café déploiement") == ["café", "déploiement"]

    def test_no_stemming(self):
        assert tokenize("deployment deployments") == ["deployment", "deployments"]


class TestKeywordWeights:
    def test_title_words_outweigh_body_words(self):
        weights = keyword_weights("Kubernetes", "kubernetes pods")
        assert weights == {"kubernetes": TITLE_WEIGHT, "pods": 1}

    def test_only_the_start_of_a_long_body_is_read(self):
        body = "x" * BODY_CHARS + " lateword"
        assert "lateword" not in keyword_weights("t", body)


class TestSimilarity:
    def test_identical_keyword_sets_score_one(self):
        weights = keyword_weights("Docker networking", "bridge overlay")
        assert similarity(weights, dict(weights)).score == 1.0

    def test_disjoint_notes_score_zero_with_no_shared_keywords(self):
        result = similarity({"alpha": 1}, {"omega": 1})
        assert (result.score, result.shared) == (0.0, ())

    def test_weighted_jaccard_value(self):
        a = {"docker": 3, "network": 1, "bridge": 1}  # title word docker
        b = {"docker": 1, "network": 1, "volume": 1}
        # shared: docker min(3,1)=1, network min(1,1)=1 -> 2 ; union: docker 3, network 1, bridge 1, volume 1 -> 6
        assert similarity(a, b).score == pytest.approx(2 / 6, abs=1e-4)

    def test_is_symmetric(self):
        a = keyword_weights("Kubernetes deployment", "rolling updates pods services")
        b = keyword_weights("Pods", "kubernetes services deployment strategy")
        assert similarity(a, b) == similarity(b, a)

    def test_is_deterministic_regardless_of_insertion_order(self):
        forward = {"zeta": 1, "alpha": 1, "mid": 3}
        backward = dict(reversed(list(forward.items())))
        other = {"alpha": 1, "mid": 1, "zeta": 3}
        assert similarity(forward, other) == similarity(backward, other)

    def test_shared_keywords_ordered_by_weight_then_alphabetically(self):
        a = {"beta": 1, "alpha": 1, "title": 3}
        b = {"beta": 1, "alpha": 1, "title": 3}
        assert similarity(a, b).shared == ("title", "alpha", "beta")

    def test_a_longer_note_does_not_dilute_a_title_match_to_nothing(self):
        short = keyword_weights("Kubernetes", "")
        long = keyword_weights("Kubernetes", " ".join(f"filler{i}" for i in range(20)))
        assert similarity(short, long).score > 0.1


class TestExplain:
    def test_lists_keywords_and_percentage(self):
        text = explain(similarity({"docker": 1, "network": 1}, {"docker": 1, "network": 1, "bridge": 1}))
        assert text == "Shared keywords: docker, network (67% keyword overlap)"

    def test_truncates_long_keyword_lists(self):
        weights = {f"word{i:02d}": 1 for i in range(12)}
        text = explain(similarity(weights, weights))
        assert text.startswith("Shared keywords: word00, word01") and "and 4 more" in text
