from typing import Iterable, Optional, Tuple
from unittest import TestCase

from polyfile.polyfile import Analyzer, Match
from polyfile.ast import Node
from polyfile.fileutils import Tempfile


class MockASTNode:
    def __init__(
            self,
            name: str,
            offset: Optional[int] = None,
            length: Optional[int] = None,
            children: Iterable["MockASTNode"] = ()
    ):
        self.name: str = name
        if offset is not None:
            setattr(self, "offset", offset)
        if length is not None:
            setattr(self, "length", length)
        self.children: Tuple[MockASTNode, ...] = tuple(children)


class ASTTest(TestCase):
    example_obj = MockASTNode(name="root", children=[
        MockASTNode(name="child1", offset=0, length=10, children=[
           MockASTNode(name="grandchild1", offset=5, length=5)
        ]),
        MockASTNode(name="child2", offset=10, length=10, children=[
            MockASTNode(name="grandchild2", offset=10, length=3),
            MockASTNode(name="grandchild3", offset=13, length=7)
        ])
    ])

    def test_ast_loading(self):
        ast = Node.load(self.example_obj)
        self.assertEqual("root", ast.name)
        self.assertEqual(0, ast.offset)
        self.assertEqual(20, ast.length)
        self.assertEqual(2, len(ast.children))
        child1, child2 = ast.children
        self.assertIsNone(child1.older_sibling)
        self.assertIs(child1, child2.older_sibling)
        self.assertEqual("child1", child1.name)
        self.assertEqual(0, child1.offset)
        self.assertEqual(10, child1.length)
        self.assertEqual(1, len(child1.children))
        grandchild1 = child1.children[0]
        self.assertEqual("grandchild1", grandchild1.name)
        self.assertEqual(5, grandchild1.offset)
        self.assertEqual(5, grandchild1.length)
        self.assertEqual("child2", child2.name)
        self.assertEqual(10, child2.offset)
        self.assertEqual(10, child2.length)
        self.assertEqual(2, len(child2.children))
        grandchild2, grandchild3 = child2.children
        self.assertIsNone(grandchild2.older_sibling)
        self.assertIs(grandchild2, grandchild3.older_sibling)
        self.assertEqual("grandchild2", grandchild2.name)
        self.assertEqual(10, grandchild2.offset)
        self.assertEqual(3, grandchild2.length)
        self.assertEqual("grandchild3", grandchild3.name)
        self.assertEqual(13, grandchild3.offset)
        self.assertEqual(7, grandchild3.length)

    def test_ast_conversion(self):
        ast = Node.load(self.example_obj)
        analyzer = Analyzer("")
        matcher = analyzer.matcher
        root_match = Match("root", None, matcher=matcher)
        matches = list(ast.to_matches(root_match))
        self.assertEqual(6, len(matches))
        for m, name in zip(matches, ("root", "child1", "grandchild1", "child2", "grandchild2", "grandchild3")):
            self.assertIs(root_match, m.root)
            self.assertEqual(name, m.name)
