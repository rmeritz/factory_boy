# -*- coding: utf-8 -*-
# Copyright (c) 2010 Mark Sandstrom
# Copyright (c) 2011-2013 Raphaël Barrois
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import warnings

from factory import base
from factory import declarations

from .compat import unittest

class TestObject(object):
    def __init__(self, one=None, two=None, three=None, four=None):
        self.one = one
        self.two = two
        self.three = three
        self.four = four

class FakeDjangoModel(object):
    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        instance.id = 1
        return instance

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)
            self.id = None

class FakeModelFactory(base.Factory):
    ABSTRACT_FACTORY = True

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        return target_class.create(**kwargs)


class TestModel(FakeDjangoModel):
    pass


class SafetyTestCase(unittest.TestCase):
    def testBaseFactory(self):
        self.assertRaises(base.FactoryError, base.BaseFactory)


class FactoryTestCase(unittest.TestCase):
    def test_factory_for(self):
        class TestObjectFactory(base.Factory):
            FACTORY_FOR = TestObject

        self.assertEqual(TestObject, TestObjectFactory.FACTORY_FOR)
        obj = TestObjectFactory.build()
        self.assertFalse(hasattr(obj, 'FACTORY_FOR'))

    def testDisplay(self):
        class TestObjectFactory(base.Factory):
            FACTORY_FOR = FakeDjangoModel

        self.assertIn('TestObjectFactory', str(TestObjectFactory))
        self.assertIn('FakeDjangoModel', str(TestObjectFactory))

    def testLazyAttributeNonExistentParam(self):
        class TestObjectFactory(base.Factory):
            FACTORY_FOR = TestObject

            one = declarations.LazyAttribute(lambda a: a.does_not_exist )

        self.assertRaises(AttributeError, TestObjectFactory)

    def testInheritanceWithSequence(self):
        """Tests that sequence IDs are shared between parent and son."""
        class TestObjectFactory(base.Factory):
            FACTORY_FOR = TestObject

            one = declarations.Sequence(lambda a: a)

        class TestSubFactory(TestObjectFactory):
            FACTORY_FOR = TestObject

            pass

        parent = TestObjectFactory.build()
        sub = TestSubFactory.build()
        alt_parent = TestObjectFactory.build()
        alt_sub = TestSubFactory.build()
        ones = set([x.one for x in (parent, alt_parent, sub, alt_sub)])
        self.assertEqual(4, len(ones))

class FactoryDefaultStrategyTestCase(unittest.TestCase):
    def setUp(self):
        self.default_strategy = base.Factory.FACTORY_STRATEGY

    def tearDown(self):
        base.Factory.FACTORY_STRATEGY = self.default_strategy

    def testBuildStrategy(self):
        base.Factory.FACTORY_STRATEGY = base.BUILD_STRATEGY

        class TestModelFactory(base.Factory):
            FACTORY_FOR = TestModel

            one = 'one'

        test_model = TestModelFactory()
        self.assertEqual(test_model.one, 'one')
        self.assertFalse(test_model.id)

    def testCreateStrategy(self):
        # Default FACTORY_STRATEGY

        class TestModelFactory(FakeModelFactory):
            FACTORY_FOR = TestModel

            one = 'one'

        test_model = TestModelFactory()
        self.assertEqual(test_model.one, 'one')
        self.assertTrue(test_model.id)

    def testStubStrategy(self):
        base.Factory.FACTORY_STRATEGY = base.STUB_STRATEGY

        class TestModelFactory(base.Factory):
            FACTORY_FOR = TestModel

            one = 'one'

        test_model = TestModelFactory()
        self.assertEqual(test_model.one, 'one')
        self.assertFalse(hasattr(test_model, 'id'))  # We should have a plain old object

    def testUnknownStrategy(self):
        base.Factory.FACTORY_STRATEGY = 'unknown'

        class TestModelFactory(base.Factory):
            FACTORY_FOR = TestModel

            one = 'one'

        self.assertRaises(base.Factory.UnknownStrategy, TestModelFactory)

    def testStubWithNonStubStrategy(self):
        class TestModelFactory(base.StubFactory):
            FACTORY_FOR = TestModel

            one = 'one'

        TestModelFactory.FACTORY_STRATEGY = base.CREATE_STRATEGY

        self.assertRaises(base.StubFactory.UnsupportedStrategy, TestModelFactory)

        TestModelFactory.FACTORY_STRATEGY = base.BUILD_STRATEGY
        self.assertRaises(base.StubFactory.UnsupportedStrategy, TestModelFactory)

    def test_change_strategy(self):
        @base.use_strategy(base.CREATE_STRATEGY)
        class TestModelFactory(base.StubFactory):
            FACTORY_FOR = TestModel

            one = 'one'

        self.assertEqual(base.CREATE_STRATEGY, TestModelFactory.FACTORY_STRATEGY)


class FactoryCreationTestCase(unittest.TestCase):
    def testFactoryFor(self):
        class TestFactory(base.Factory):
            FACTORY_FOR = TestObject

        self.assertTrue(isinstance(TestFactory.build(), TestObject))

    def testStub(self):
        class TestFactory(base.StubFactory):
            pass

        self.assertEqual(TestFactory.FACTORY_STRATEGY, base.STUB_STRATEGY)

    def testInheritanceWithStub(self):
        class TestObjectFactory(base.StubFactory):
            FACTORY_FOR = TestObject

            pass

        class TestFactory(TestObjectFactory):
            pass

        self.assertEqual(TestFactory.FACTORY_STRATEGY, base.STUB_STRATEGY)

    def testCustomCreation(self):
        class TestModelFactory(FakeModelFactory):
            FACTORY_FOR = TestModel

            @classmethod
            def _prepare(cls, create, **kwargs):
                kwargs['four'] = 4
                return super(TestModelFactory, cls)._prepare(create, **kwargs)

        b = TestModelFactory.build(one=1)
        self.assertEqual(1, b.one)
        self.assertEqual(4, b.four)
        self.assertEqual(None, b.id)

        c = TestModelFactory(one=1)
        self.assertEqual(1, c.one)
        self.assertEqual(4, c.four)
        self.assertEqual(1, c.id)

    # Errors

    def test_no_associated_class(self):
        try:
            class Test(base.Factory):
                pass
            self.fail()
        except base.Factory.AssociatedClassError as e:
            self.assertTrue('autodiscovery' not in str(e))


class PostGenerationParsingTestCase(unittest.TestCase):

    def test_extraction(self):
        class TestObjectFactory(base.Factory):
            FACTORY_FOR = TestObject

            foo = declarations.PostGenerationDeclaration()

        self.assertIn('foo', TestObjectFactory._postgen_declarations)

    def test_classlevel_extraction(self):
        class TestObjectFactory(base.Factory):
            FACTORY_FOR = TestObject

            foo = declarations.PostGenerationDeclaration()
            foo__bar = 42

        self.assertIn('foo', TestObjectFactory._postgen_declarations)
        self.assertIn('foo__bar', TestObjectFactory._declarations)



if __name__ == '__main__':
    unittest.main()
