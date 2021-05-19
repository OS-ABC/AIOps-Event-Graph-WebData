#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Template(object):
    def __init__(self, index, words, logid):
        self._index = index
        self._words = words
        self._nwords = len(words)
        self._counts = 1
        self._logid = [logid]

    @property
    def index(self):
        return self._index

    @property
    def words(self):
        return self._words

    @property
    def nwords(self):
        return self._nwords

    @property
    def counts(self):
        return self._counts

    def _dump_as_json(self):
        """Dumps the data structure as a JSON format to serialize the
        object.

        This internal function is called by the TemplateManager
        class.
        """
        assert(False)

    def _restore_from_json(self, data):
        """Initializes the instance with the provided JSON data.

        This internal function is normally called by the initializer.
        """
        assert(False)

    def get_similarity_score(self, new_words):
        """Retruens a similarity score.

        Args:
          new_words: An array of words.

        Returns:
          score: in float.
        """
        assert(False)

    def update(self, new_words):
        """Updates the template data using the supplied new_words.
        """
        assert(False)

    def __str__(self):
        template = ' '.join([self.words[idx] if self.words[idx] != '' else '*' for idx in range(self.nwords)])
        return '{index}({nwords})({counts}):{template}'.format(
            index=self.index,
            nwords=self.nwords,
            counts=self._counts,
            template=' '.join([self.words[idx] if self.words[idx] != '' else '*' for idx in range(self.nwords)]))

class TemplateManager(object):
    def __init__(self):
        self._templates = []

    @property
    def templates(self):
        return self._templates

    def infer_template(self, words):
        """Infer the best matching template, or create a new template if there
        is no similar template exists.

        Args:
          words: An array of words.

        Returns:
          A template instance.

        """
        assert(False)


    def dump_template(self, index):
        """Dumps a specified template data structure usually in a text
        format.

        Args:
          index: a template index.

        Returns:
          A serialized text data of the specified template.
        """
        assert(False)

    def restore_template(self, data):
        """Creates a template instance from data (usually a serialized
        data when LogDatabase.close() method is called.

        This function is called by the LogDatabase class.

        Args:
          data: a data required to rebuild a template instance.

        Returns:
          A template instance.
        """
        assert(False)

    def _append_template(self, template):
        """Append a template.

        This internal function may be called by the LogDatabase
        class too.

        Args:
          template: a new template to be appended.

        Returns:
          template: the appended template.
        """
        assert(template.index == len(self.templates))
        self.templates.append(template)
        return template
