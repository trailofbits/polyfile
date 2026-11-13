from abc import ABC, abstractmethod
from collections import defaultdict
import base64
import hashlib
from importlib.metadata import version
from json import dumps
from mimetypes import guess_extension
from pathlib import Path
from time import localtime
import traceback
from typing import Any
from collections.abc import Callable, Iterable, Iterator

from polyfile.analysis import AnalysisContext, AnalysisLimits
from polyfile.fileutils import FileStream, Streamable
from . import logger
from .magic import MagicMatcher, Match as MagicMatch, MatchContext, TestResult

__version__: str = version("polyfile")
del version
mod_year = localtime(Path(__file__).stat().st_mtime).tm_year
__copyright__: str = f"Copyright ©{mod_year} Trail of Bits"
__license__: str = "Apache License Version 2.0 https://www.apache.org/licenses/"

ParserFunction = Callable[[FileStream, "Match"], Iterator["Match"]]


class Parser(ABC):
    @abstractmethod
    def parse(self, stream: FileStream, match: "Match") -> Iterator["Match"]:
        raise NotImplementedError()

    def __call__(self, stream: FileStream, match: "Match") -> Iterator["Match"]:
        yield from self.parse(stream, match)

    def __hash__(self):
        return id(self)

    def __str__(self):
        return self.__class__.__name__


class ParserFunctionWrapper(Parser):
    def __init__(self, parser: ParserFunction):
        self.parser: ParserFunction = parser

    def __hash__(self):
        return hash(self.parser)

    def parse(self, stream: FileStream, match: "Match") -> Iterator["Match"]:
        yield from self.parser(stream, match)

    def __str__(self):
        if hasattr(self.parser, "__qualname__"):
            return self.parser.__qualname__
        elif hasattr(self.parser, "__name__"):
            return self.parser.__name__
        else:
            return self.parser.__class__.__name__


PARSERS: dict[str, set[Parser]] = defaultdict(set)

log = logger.getStatusLogger("polyfile")


class InvalidMatch(ValueError):
    pass


class Match:
    def __init__(
            self,
            name: str,
            match_obj: Any,
            relative_offset: int = 0,
            length: int | None = None,
            parent: 'Match | None' = None,
            matcher: 'Matcher | None' = None,
            display_name: str | None = None,
            img_data: str | None = None,
            decoded: bytes | None = None,
            extension: str | None = None,
            *,
            description: str | None = None,
            analysis_context: AnalysisContext | None = None,
            analysis_depth: int | None = None,
            source: str | None = None
    ):
        self._children: list[Match] = []
        self.name: str = name
        self.matcher: Matcher | None = None
        self.match = match_obj
        self.description: str | None = description
        self.img_data: str | None = img_data
        self.decoded: bytes | None = decoded
        self._offset: int = relative_offset
        self._length: int | None = length
        self._parent: Match | None = parent
        self.source = source if source is not None else (
            parent.source if parent is not None else "file"
        )
        if parent is not None:
            if not isinstance(parent, Match):
                raise ValueError("The parent must be an instance of a Match")
            parent._children.append(self)
            if matcher is None:
                matcher = parent.matcher
        if matcher is None:
            raise(ValueError("A Match must be initialized with `parent` and/or `matcher` not being None"))
        self.matcher = matcher
        if parent is not None:
            analysis_context = parent.analysis_context
        self.analysis_context = analysis_context or AnalysisContext(matcher.limits)
        if analysis_depth is None:
            analysis_depth = parent.analysis_depth if parent is not None else 0
        self.analysis_depth = analysis_depth
        self.analysis_member_counted = False
        self.analysis_skip_parsers: set[str] = set()
        self.analysis_status: str | None = None
        self.analysis_message: str | None = None
        if display_name is None:
            self.display_name: str = name
        else:
            self.display_name = display_name
        self.extension: str | None = extension
        if extension is None:
            self.extension = guess_extension(self.name)
            if self.extension is not None and self.extension.startswith("."):
                # guess_extension adds a leading dot
                self.extension = self.extension[1:]

    @property
    def children(self) -> tuple["Match", ...]:
        return tuple(self._children)

    def __len__(self):
        return len(self._children)

    def __iter__(self) -> Iterator["Match"]:
        return iter(self._children)

    def __getitem__(self, index: int) -> "Match":
        return self._children[index]

    @property
    def parent(self) -> 'Match | None':
        return self._parent

    @property
    def offset(self) -> int:
        """The offset within this match's physical or decoded source buffer."""
        if self.parent is not None and self.parent.source == self.source:
            return self.parent.offset + self.relative_offset
        else:
            return self.relative_offset

    @property
    def root(self) -> "Match":
        if self.parent is None:
            return self
        else:
            return self.parent.root

    @property
    def root_offset(self) -> int:
        if self.root.source == self.source:
            return self.offset - self.root.offset
        return self.offset

    @property
    def relative_offset(self) -> int:
        """The offset of this match relative to its parent"""
        return self._offset

    @property
    def length(self) -> int:
        """The number of bytes in the match"""
        if self._length is None:
            if self._children:
                children = [c for c in self._children if c.source == self.source]
                return max((c.offset + c.length for c in children), default=self.offset) - self.offset
            else:
                return 0
        return self._length

    def to_obj(self):
        """Renders this match as the SBUD element that `docs/json_format.md` describes.

        An explicit `description` supplies the rendered value while retaining the original
        match object. A match with neither a description nor a `match_obj` describes no content
        of its own, so the element it renders carries no `value` key. Any other match object
        becomes the `value` through `str`, so a match may only hold an object whose `str` derives
        from the bytes
        it matched. The default `object.__str__` does not: it embeds a heap address, which
        differs between runs over the same input.

        Returns:
            The SBUD element, with one entry in `subEls` for each child match.
        """
        ret = {
            'relative_offset': self.relative_offset,
            'offset': self.offset,
            'size': self.length,
            'type': self.name,
            'name': self.display_name,
            'source': self.source,
        }
        if self.description is not None:
            ret['value'] = self.description
        elif self.match is not None:
            ret['value'] = str(self.match)
        ret['subEls'] = [c.to_obj() for c in self]
        if self.img_data is not None:
            ret['img_data'] = self.img_data
        if self.decoded is not None:
            ret['decoded'] = base64.b64encode(self.decoded).decode('utf-8')
        if self.extension is not None:
            ret['extension'] = self.extension
        if self.analysis_status is not None:
            ret['analysis_status'] = self.analysis_status
            ret['analysis_message'] = self.analysis_message
        return ret

    def json(self) -> str:
        return dumps(self.to_obj())

    def __repr__(self):
        return f"{self.__class__.__name__}(match={self.match!r}, relative_offset={self._offset}, parent={self._parent!r})"

    def __str__(self):
        return f"Match<{self.match}>@{self._offset}"


class Submatch(Match):
    pass


def register_parser(*filetypes: str) -> Callable[[Parser | ParserFunction], Parser]:
    def wrapper(parser: Parser | ParserFunction) -> Parser:
        if not isinstance(parser, Parser):
            parser = ParserFunctionWrapper(parser)
        for ft in filetypes:
            PARSERS[ft].add(parser)
        return parser
    return wrapper


class Matcher:
    def __init__(self, parse: bool = True, matcher: MagicMatcher | None = None,
                 *, limits: AnalysisLimits | None = None):
        if matcher is None:
            self.magic_matcher: MagicMatcher = MagicMatcher.DEFAULT_INSTANCE
        else:
            self.magic_matcher = matcher
        self.parse: bool = parse
        self.limits = limits or AnalysisLimits()

    def handle_mimetype(
            self, mimetype: str,
            match_obj: TestResult,
            data: bytes,
            file_stream: Streamable,
            parent: Match | None = None,
            offset: int = 0,
            length: int | None = None,
            *,
            description: str | None = None,
            analysis_context: AnalysisContext | None = None,
            analysis_depth: int = 0
    ) -> Iterator[Match]:
        if length is None:
            length = len(data) - offset
        extension: str | None = None
        try:
            extension = next(iter(match_obj.test.all_extensions))
        except StopIteration:
            pass
        m = Match(
            mimetype,
            match_obj,
            offset,
            length=length,
            parent=parent,
            matcher=self,
            extension=extension,
            description=description,
            analysis_context=analysis_context,
            analysis_depth=analysis_depth
        )
        yield m
        if self.parse and (parent is None or mimetype not in parent.analysis_skip_parsers):
            for parser in PARSERS[mimetype]:
                # Don't yield this custom match until we've tried its submatch function
                # (which may throw an InvalidMatch, meaning that this match is invalid)
                try:
                    with FileStream(file_stream, start=offset, length=length) as fs:
                        submatch_iter = parser(fs, m)
                        try:
                            first_submatch = next(submatch_iter)
                        except StopIteration:
                            pass
                        else:
                            yield first_submatch
                            yield from submatch_iter
                except InvalidMatch:
                    pass
                except Exception as e:
                    log.warning(f"Parser {parser!s} for MIME type {mimetype} raised an exception while "
                                f"parsing {match_obj!s} in {file_stream!s}: {e!s}")
                    if log.isEnabledFor(logger.logging.DEBUG):
                        traceback.print_exc()

    def identify(
            self, file_stream: Streamable
    ) -> Iterator[MagicMatch]:
        with FileStream(file_stream) as f:
            context = MatchContext.load(f, only_match_mime=False)
            yield from self.magic_matcher.match(context)

    def match(self, file_stream: Streamable,
              parent: Match | None = None) -> Iterator[Match]:
        analysis_context = (
            parent.analysis_context if parent is not None else AnalysisContext(self.limits)
        )
        depth = parent.analysis_depth + 1 if parent is not None else 0
        with FileStream(file_stream) as f:
            if parent is not None:
                reason = analysis_context.claim_member(
                    len(f), depth, count=not parent.analysis_member_counted,
                )
                if reason is not None:
                    parent.analysis_status = "limited"
                    parent.analysis_message = reason
                    return
            matched_mimetypes: set[str] = set()
            magic_context = MatchContext.load(f, only_match_mime=True)
            is_elf = magic_context.data.startswith(b"\x7fELF")
            magic_context.only_match_mime = not is_elf
            for magic_match in self.magic_matcher.match(magic_context):
                description = None
                if is_elf and magic_match._soft_magic_message().startswith("ELF "):
                    description = magic_match.description()
                for result in magic_match:
                    if result.test.mime is None:
                        continue
                    mimetype = result.test.mime.resolve(magic_context)
                    if mimetype in matched_mimetypes:
                        continue
                    matched_mimetypes.add(mimetype)
                    yield from self.handle_mimetype(
                        mimetype, result, magic_context.data, f, parent,
                        description=description,
                        analysis_context=analysis_context, analysis_depth=depth,
                    )


class Analyzer:
    def __init__(self, path: str | Path, parse: bool = True,
                 magic_matcher: MagicMatcher | None = None,
                 *, limits: AnalysisLimits | None = None):
        self.path: str | Path = path
        self.parse: bool = parse
        self._magic_matcher: MagicMatcher | None = magic_matcher
        self.limits = limits or AnalysisLimits()
        self._matcher: Matcher | None = None
        self._matches: list[Match] | None = None
        self._match_iterator: Iterator[Match] | None = None
        self._magic_matches: list[MagicMatch] | None = None
        self._magic_match_iterator: Iterator[MagicMatch] | None = None

    @property
    def magic_matcher(self) -> MagicMatcher:
        if self._magic_matcher is None:
            return MagicMatcher.DEFAULT_INSTANCE
        else:
            return self._magic_matcher

    def mime_types(self) -> Iterator[tuple[str, MagicMatch]]:
        mimetypes: dict[str, set[str]] = {}
        with open(self.path, "rb") as f:
            for match in self.magic_matcher.match(MatchContext.load(f, only_match_mime=True)):
                for mimetype in match.mimetypes:
                    match_text = str(match)
                    if mimetype not in mimetypes:
                        mimetypes[mimetype] = set()
                    if match_text not in mimetypes[mimetype]:
                        yield mimetype, match
                        mimetypes[mimetype].add(match_text)

    @property
    def matcher(self) -> Matcher:
        if self._matcher is None:
            self._matcher = Matcher(parse=self.parse, matcher=self.magic_matcher,
                                    limits=self.limits)
        return self._matcher

    @property
    def matches_so_far(self) -> list[Match] | None:
        return self._matches

    @property
    def magic_matches_so_far(self) -> list[MagicMatch] | None:
        return self._magic_matches

    def matches(self) -> Iterator[Match]:
        if self._matches is None or self._match_iterator is not None:
            if self._matches is None:
                self._matches = []
                self._match_iterator = iter(self.matcher.match(self.path))
            else:
                yield from self._matches
            while self._match_iterator is not None:
                try:
                    match = next(self._match_iterator)
                except StopIteration:
                    self._match_iterator = None
                    break
                if hasattr(match.match, "filetype"):
                    filetype = match.match.filetype
                else:
                    filetype = match.name
                if match.parent is None:
                    log.info(f"Found a file of type {filetype} at byte offset {match.offset}")
                    self._matches.append(match)
                    yield match
                elif isinstance(match, Submatch):
                    log.debug(f"Found a subregion of type {filetype} at byte offset {match.offset}")
                else:
                    log.info(f"Found an embedded file of type {filetype} at byte offset {match.offset}")
        else:
            yield from self._matches

    def magic_matches(self) -> Iterator[MagicMatch]:
        if self._magic_matches is None or self._magic_match_iterator is not None:
            if self._magic_matches is None:
                self._magic_matches = []
                self._magic_match_iterator = iter(self.matcher.identify(self.path))
            else:
                yield from self._magic_matches
            while self._magic_match_iterator is not None:
                try:
                    match = next(self._magic_match_iterator)
                    yield match
                except StopIteration:
                    self._magic_match_iterator = None
                    break
        else:
            yield from self._magic_matches

    def sbud(self, matches: Iterable[Match] | None = None, include_contents: bool = True) -> dict[str, Any]:
        """Builds the SBuD object that describes this file.

        Args:
            matches: the matches to record. Defaults to running the analysis with
                :meth:`Analyzer.matches`. Whatever is passed is materialized before the tree is
                built, so this is an optimization for a caller that already has the matches, never
                a precondition.
            include_contents: whether to base64 encode the whole input into the ``b64contents`` key.
                Pass ``False`` to skip the encoding, which omits the key rather than emitting an
                empty one, so a caller that needs the contents fails with a ``KeyError`` instead of
                reading the input as empty.

        Returns:
            The SBuD object, ready to serialize as JSON.
        """
        # `Analyzer.matches` yields a top-level match as soon as it is found and attaches its
        # children as it goes, so `to_obj` has to run after the whole analysis rather than against
        # a half-drained generator. A supplied iterable is materialized for the same reason: a
        # caller cannot know how far this needs it drained.
        matches = list(self.matches() if matches is None else matches)
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()
        b64contents: str | None = None
        with open(self.path, 'rb') as hash_file:
            data = hash_file.read()
            md5.update(data)
            sha1.update(data)
            sha256.update(data)
            if include_contents:
                b64contents = base64.b64encode(data).decode('utf-8')
            file_length = len(data)
            del data
        sbud: dict[str, Any] = {
            'MD5': md5.hexdigest(),
            'SHA1': sha1.hexdigest(),
            'SHA256': sha256.hexdigest(),
        }
        if b64contents is not None:
            sbud['b64contents'] = b64contents
        sbud.update({
            'fileName': self.path,
            'length': file_length,
            'versions': {
                'polyfile': __version__
            },
            'struc': [
                match.to_obj() for match in matches
            ]
        })
        return sbud
