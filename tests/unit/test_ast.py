from typing import Iterable, Optional, Tuple
from unittest import TestCase

from polyfile.ast import Node


class TestASTNode:
    def __init__(
            self,
            name: str,
            offset: Optional[int] = None,
            length: Optional[int] = None,
            children: Iterable["TestASTNode"] = ()
    ):
        self.name: str = name
        if offset is not None:
            setattr(self, "offset", offset)
        if length is not None:
            setattr(self, "length", length)
        self.children: Tuple[TestASTNode, ...] = tuple(children)


class ASTTest(TestCase):
    example_obj = TestASTNode(name="root", children=[
        TestASTNode(name="child1", offset=0, length=10, children=[
           TestASTNode(name="grandchild1", offset=5, length=5)
        ]),
        TestASTNode(name="child2", offset=10, length=10, children=[
            TestASTNode(name="grandchild2", offset=10, length=3),
            TestASTNode(name="grandchild3", offset=13, length=7)
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
