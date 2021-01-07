from typing import List, Optional

from builders import IdiomMatcherBuilder
from spacy import Language, Vocab
from spacy.matcher import Matcher
from spacy.tokens import Doc


# factory method for the component
@Language.factory(
    name="merge_idioms",
    retokenizes=True,  # we are merging, so it does retokenize
)
def create_component(nlp: Language, name: str) -> 'MergeIdiomsComponent':
    return MergeIdiomsComponent(nlp.vocab, name)


class MergeIdiomsComponent:
    """
    why define the whole class?
    because It has to maintain a reference to an instance of idiom_matcher.
    """

    def __init__(self, vocab: Vocab, name: str):
        # these..must be json serializable
        self.vocab = vocab
        self.name = name  # not sure if this will ever be useful
        # reconstruct idiom matcher here - it'll only be executed once
        # what if you build idiom matcher here?
        # yeah, that makes sense - then, you have to include
        # this may take some time, but once done, you don't need to repeat them.
        self.idiom_matcher = self.build_idiom_matcher()

    def __call__(self, doc: Doc) -> Doc:
        # use lowercase version of the doc.
        matches = self.idiom_matcher(doc)
        matches = self.greedily_normalize(matches)
        for vocab_id, start, end in matches:
            # get back the lemma for this match
            # note: matcher has references to the vocab on its own!
            idiom_lemma = self.idiom_matcher.vocab.strings[vocab_id]
            # retokenise
            with doc.retokenize() as retokeniser:
                # try:
                retokeniser.merge(doc[start:end],
                                  # set tag as idiom
                                  # TODO: make sure you give it vocab_id.
                                  attrs={'LEMMA': idiom_lemma, 'TAG': 'IDIOM'})
                # except ValueError as ve:
                #     print("pass merging for:" + match_lemma)
                #     pass
        return doc

    def build_idiom_matcher(self) -> Matcher:
        # create a new instance here
        # have to do make this every single time
        # because matcher is not JSON serializable.
        idiom_matcher_builder = IdiomMatcherBuilder()
        idiom_matcher_builder.construct(self.vocab)
        return idiom_matcher_builder.idiom_matcher

    # need this to fix the duplicate issue.
    def greedily_normalize(self, matches: List[Optional[tuple]]) -> List[tuple]:
        """
        have to do this to prevent the case like:
        e.g.
        It's not the end of the world;
        -> will match both "end of the world" and "not the end of the world"
        In such cases, we'd better leave out the superset.
        """
        # first, find the subset
        to_del: List[int] = list()
        for i, match_i in enumerate(matches):
            lemma_i = self.idiom_matcher.vocab.strings[match_i[0]]
            for j, match_j in enumerate(matches):
                lemma_j = self.idiom_matcher.vocab.strings[match_j[0]]
                if j != i:  # only if they are different
                    if lemma_j in lemma_i:
                        to_del.append(j)
        else:
            for del_idx in to_del:
                # delete the reference to the items
                # not necessarily the items itself.
                matches[del_idx] = None
            else:
                return [
                    match
                    for match in matches
                    if match
                ]
