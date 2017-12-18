# -*- coding: utf-8 -*-

"""
file: module_liedataframe_test.py

Test the pylie DataFrameBase methods common to all
DataFrame types in the package
"""

import os
import unittest2

from pandas import DataFrame, read_csv

from pylie import LIEDataFrame


class TestLIEDataFrameBase(unittest2.TestCase):
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files'))
    tempfiles = []

    def setUp(self):
        """
        Import processed LIE VdW and Coulomb energies for several cases into a LIEDataFrame
        """

        cyp1a2 = os.path.join(self.filepath, 'liedata_CYP1a2.csv')
        self.liedata = LIEDataFrame(read_csv(cyp1a2))
        if 'Unnamed: 0' in self.liedata:
            del self.liedata['Unnamed: 0']

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the working directory
        """

        for tmpfile in self.tempfiles:
            if os.path.isfile(tmpfile):
                os.remove(tmpfile)

        self.tempfiles = []

    def test_dataframe_types(self):
        """
        Test class instance
        """

        self.assertIsInstance(self.liedata, DataFrame)
        self.assertIsInstance(self.liedata, LIEDataFrame)
        self.assertEqual(self.liedata._class_name, 'dataframe')

    def test_dataframe_export(self):
        """
        Export LIEDataFrame in different file formats.
        This is handled by pandas functionality
        """

        self.liedata['filter_mask'] = 0

        formats = {'to_csv': 'csv', 'to_excel': 'xlsx', 'to_json': 'json', 'to_html': 'html', 'to_string': 'tbl'}
        for fmt in formats:
            if hasattr(self.liedata, fmt):
                method = getattr(self.liedata, fmt)

                # Export to file
                export = os.path.join(self.filepath, 'export.{0}'.format(formats[fmt]))
                with open(export, 'w') as outf:
                    method(outf)

                self.tempfiles.append(export)
                self.assertTrue(os.path.isfile(export))

    def test_dataframe_get_cases(self):
        """
        Test LIEDataFrame get_cases method
        """

        # Unaltered LIEDataFrame
        self.assertEqual(self.liedata.cases, [1, 2, 4, 6, 7, 9, 10, 11, 12, 13, 14, 16, 17, 20, 23, 25, 27, 28, 29, 30,
                                              31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 50, 51, 52, 53, 54,
                                              55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72,
                                              73])

        # Selection made using get_cases
        selection = self.liedata.get_cases([1, 12, 13, 30, 71])
        self.assertEqual(selection.cases, [1, 12, 13, 30, 71])
        self.assertEqual(len(selection), 32)

        # Empty DataFrame if no match
        selection = self.liedata.get_cases([100, 101, 102])
        self.assertTrue(selection.empty)

    def test_dataframe_get_poses(self):
        """
        Test LIEDataFrame get_poses method
        """

        # Make selection
        selection = self.liedata.get_poses([(1, 1), (30, 4), (30, 3), (40, 2)])
        self.assertEqual(selection.cases, [1, 30, 40])
        self.assertEqual(len(selection), 4)

        # Empty DataFrame if no match
        selection = self.liedata.get_poses([(40, 8)])
        self.assertTrue(selection.empty)

    def test_dataframe_get_columns(self):
        """
        Test LIEDataFrame get_columns method.
        Get one or multiple columns headers as list with optional wildcard
        support. List can subsequently be used to get the actual columns
        using Pandas query methods.
        """

        # Select column names
        self.assertListEqual(self.liedata.get_columns('case'), ['case'])
        self.assertListEqual(self.liedata.get_columns([u'filter_mask', u'poses']), [u'filter_mask', u'poses'])
        self.assertListEqual(self.liedata.get_columns('coul_*'), ['coul_bound', 'coul_unbound'])
        self.assertListEqual(self.liedata.get_columns([u'vdw*', u'poses']),
                             ['vdw_unbound', 'vdw_bound', 'vdw', u'poses'])
        self.assertListEqual(self.liedata.get_columns('not_exist'), [])

        # Select actual columns
        selection = self.liedata.loc[:, self.liedata.get_columns('coul_*')]
        self.assertFalse(selection.empty)
        self.assertEqual(list(selection.columns), ['coul_bound', 'coul_unbound'])

    def test_trainset_methods(self):
        """
        Test LIEDataFrame methods for getting and setting training sets
        Resetting the train mask will label all cases with 0 in the train_mask
        which results in all cases being test cases.
        """

        # Reset train mask
        self.liedata.reset_trainset()
        self.assertTrue(self.liedata.trainset.empty)

        # Define a train set
        trainset = [1, 12, 13, 30, 71]
        self.liedata.trainset = trainset
        self.assertListEqual(self.liedata.trainset.cases, trainset)
        self.assertEqual(len(self.liedata.trainset), 32)

        # Everything else should be test set
        testset = set(self.liedata.cases).difference(set(trainset))
        self.assertListEqual(self.liedata.testset.cases, list(testset))

        # Define trainset case-pose combinations and add them to the ones
        # already defined
        trainsetp = [(43, 1), (43, 2), (62, 3)]
        self.liedata.trainset = trainsetp
        self.assertListEqual(self.liedata.trainset.cases, sorted(trainset+[43, 62]))

        cp = self.liedata.trainset.casepose
        self.assertEqual(len(self.liedata.trainset), len(cp))

        # Non-existing cases or case-pose combinations are filtered
        self.liedata.trainset = [123, (43, 10)]
        self.assertEqual(len(self.liedata.trainset), len(cp))

    def test_testset_methods(self):
        """
        Test LIEDataFrame methods for getting and setting training sets
        Reset the test mask using reset_traintest with train=True to make
        all cases train cases.
        """

        # Reset train mask
        self.liedata.reset_trainset(train=True)
        self.assertTrue(self.liedata.testset.empty)

        # Define a test set
        testset = [1, 12, 13, 30, 71]
        self.liedata.testset = testset
        self.assertListEqual(self.liedata.testset.cases, testset)
        self.assertEqual(len(self.liedata.testset), 32)

        # Everything else should be test set
        trainset = set(self.liedata.cases).difference(set(testset))
        self.assertListEqual(self.liedata.trainset.cases, list(trainset))

        # Define testset case-pose combinations and add them to the ones
        # already defined
        testsetp = [(43, 1), (43, 2), (62, 3)]
        self.liedata.testset = testsetp
        self.assertListEqual(self.liedata.testset.cases, sorted(testset+[43, 62]))

        cp = self.liedata.testset.casepose
        self.assertEqual(len(self.liedata.testset), len(cp))

        # Non-existing cases or case-pose combinations are filtered
        self.liedata.testset = [123, (43, 10)]
        self.assertEqual(len(self.liedata.testset), len(cp))

    def test_outliers_methods(self):
        """
        Test LIEDataFrame methods for getting and setting outlier cases
        """

        # Reset the outlier mask, everything becomes an inlier
        self.liedata.reset_outliers()
        self.assertTrue(self.liedata.outliers.empty)

        # Set outlier cases
        outlier = [1, 12, 13, 30, 71]
        self.liedata.outliers = outlier
        self.assertListEqual(self.liedata.outliers.cases, outlier)
        self.assertEqual(len(self.liedata.outliers), 32)

        # Everything else should be inliers
        inliers = set(self.liedata.cases).difference(set(outlier))
        self.assertListEqual(self.liedata.inliers.cases, list(inliers))

        # Define outlier case-pose combinations and add them to the ones
        # already defined
        outlierp = [(43, 1), (43, 2), (62, 3)]
        self.liedata.outliers = outlierp
        self.assertListEqual(self.liedata.outliers.cases, sorted(outlier+[43, 62]))

        cp = self.liedata.outliers.casepose
        self.assertEqual(len(self.liedata.outliers), len(cp))

        # Non-existing cases or case-pose combinations are filtered
        self.liedata.outliers = [123, (43, 10)]
        self.assertEqual(len(self.liedata.outliers), len(cp))

    def test_inliers_methods(self):
        """
        Test LIEDataFrame methods for getting and setting inlier cases
        """

        # Reset the outlier mask, everything becomes an outlier
        self.liedata.reset_outliers(inlier=True)
        self.assertTrue(self.liedata.inliers.empty)

        # Set outlier cases
        inliers = [1, 12, 13, 30, 71]
        self.liedata.inliers = inliers
        self.assertListEqual(self.liedata.inliers.cases, inliers)
        self.assertEqual(len(self.liedata.inliers), 32)

        # Everything else should be inliers
        outliers = set(self.liedata.cases).difference(set(inliers))
        self.assertListEqual(self.liedata.outliers.cases, list(outliers))

        # Define outlier case-pose combinations and add them to the ones
        # already defined
        inliersp = [(43, 1), (43, 2), (62, 3)]
        self.liedata.inliers = inliersp
        self.assertListEqual(self.liedata.inliers.cases, sorted(inliers+[43, 62]))

        cp = self.liedata.inliers.casepose
        self.assertEqual(len(self.liedata.inliers), len(cp))

        # Non-existing cases or case-pose combinations are filtered
        self.liedata.inliers = [123, (43, 10)]
        self.assertEqual(len(self.liedata.inliers), len(cp))
