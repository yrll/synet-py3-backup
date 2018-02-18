import unittest

import z3
from nose.plugins.attrib import attr

from synet.topo.bgp import ActionSetNextHop
from synet.topo.bgp import ActionSetLocalPref
from synet.topo.bgp import ActionSetCommunity
from synet.topo.bgp import ActionSetPeer
from synet.topo.bgp import ActionSetPrefix
from synet.topo.bgp import Access
from synet.topo.bgp import ActionPermitted
from synet.topo.bgp import Announcement
from synet.topo.bgp import BGP_ATTRS_ORIGIN
from synet.topo.bgp import Community
from synet.topo.bgp import CommunityList
from synet.topo.bgp import IpPrefixList
from synet.topo.bgp import MatchAsPath
from synet.topo.bgp import MatchAsPathLen
from synet.topo.bgp import MatchCommunitiesList
from synet.topo.bgp import MatchIpPrefixListList
from synet.topo.bgp import MatchLocalPref
from synet.topo.bgp import MatchPeer
from synet.topo.bgp import MatchNextHop
from synet.topo.bgp import RouteMap
from synet.topo.bgp import RouteMapLine
from synet.utils.fnfree_policy import SMTActions
from synet.utils.fnfree_policy import SMTSetAttribute
from synet.utils.fnfree_policy import SMTMatch
from synet.utils.fnfree_policy import SMTMatchASPath
from synet.utils.fnfree_policy import SMTMatchASPathLen
from synet.utils.fnfree_policy import SMTMatchAll
from synet.utils.fnfree_policy import SMTMatchAnd
from synet.utils.fnfree_policy import SMTMatchAttribute
from synet.utils.fnfree_policy import SMTMatchCommunity
from synet.utils.fnfree_policy import SMTMatchLocalPref
from synet.utils.fnfree_policy import SMTMatchOr
from synet.utils.fnfree_policy import SMTMatchOrigin
from synet.utils.fnfree_policy import SMTMatchPeer
from synet.utils.fnfree_policy import SMTMatchPermitted
from synet.utils.fnfree_policy import SMTMatchPrefix
from synet.utils.fnfree_policy import SMTMatchSelectOne
from synet.utils.fnfree_policy import SMTMatchMED
from synet.utils.fnfree_policy import SMTMatchNextHop
from synet.utils.fnfree_policy import SMTSelectorMatch
from synet.utils.fnfree_policy import SMTSetASPath
from synet.utils.fnfree_policy import SMTSetASPathLen
from synet.utils.fnfree_policy import SMTSetCommunity
from synet.utils.fnfree_policy import SMTSetLocalPref
from synet.utils.fnfree_policy import SMTSetOne
from synet.utils.fnfree_policy import SMTSetOrigin
from synet.utils.fnfree_policy import SMTSetPeer
from synet.utils.fnfree_policy import SMTSetPermitted
from synet.utils.fnfree_policy import SMTSetPrefix
from synet.utils.fnfree_policy import SMTSetMED
from synet.utils.fnfree_policy import SMTSetNextHop
from synet.utils.fnfree_policy import SMTRouteMap
from synet.utils.fnfree_policy import SMTRouteMapLine
from synet.utils.fnfree_smt_context import ASPATH_SORT
from synet.utils.fnfree_smt_context import BGP_ORIGIN_SORT
from synet.utils.fnfree_smt_context import PEER_SORT
from synet.utils.fnfree_smt_context import PREFIX_SORT
from synet.utils.fnfree_smt_context import NEXT_HOP_SORT
from synet.utils.fnfree_smt_context import SolverContext
from synet.utils.fnfree_smt_context import VALUENOTSET
from synet.utils.fnfree_smt_context import get_as_path_key
from synet.utils.fnfree_smt_context import read_announcements


__author__ = "Ahmed El-Hassany"
__email__ = "a.hassany@gmail.com"


@attr(speed='fast')
class TestSMTMatchAttribute(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_enum_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)
        # Provide concrete value for the match
        p1_val = prefix_sort.get_symbolic_value('Prefix1')
        p1_sym = ctx.create_fresh_var(prefix_sort, value=p1_val)
        # Act
        match = SMTMatchAttribute('prefix', p1_sym, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)

    def test_match_enum_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)
        p1_sym = ctx.create_fresh_var(prefix_sort)
        # Act
        match = SMTMatchAttribute('prefix', p1_sym, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(p1_sym.get_value(), concrete_anns[0].prefix)
        self.assertNotEquals(p1_sym.get_value(), concrete_anns[1].prefix)

    def test_match_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        pref = ctx.create_fresh_var(z3.IntSort(), value=100)
        # Act
        match = SMTMatchAttribute('local_pref', pref, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        ann1_value = match.is_match(sym_anns[1]).get_value()
        solver = z3.Solver()
        z3.reset_params()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertTrue(ann0_is_concrete)
        self.assertTrue(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertFalse(ann1_value)
        self.assertEquals(is_sat, z3.sat)

    def test_match_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Provide symbolic variable for the match
        pref = ctx.create_fresh_var(z3.IntSort())
        # Act
        match = SMTMatchAttribute('local_pref', pref, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(pref.get_value(), concrete_anns[0].local_pref)
        self.assertNotEquals(pref.get_value(), concrete_anns[1].local_pref)


@attr(speed='fast')
class TestSMTMatchCommunity(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        value = ctx.create_fresh_var(z3.BoolSort(), value=True)
        # Provide concrete value for the match
        c1 = Community("100:16")
        # Act
        match = SMTMatchCommunity(c1, value, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        ann1_value = match.is_match(sym_anns[1]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertTrue(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertFalse(ann1_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())


@attr(speed='fast')
class TestSMTMatchAnd(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)
        p1_val = prefix_sort.get_symbolic_value('Prefix1')
        prefix = ctx.create_fresh_var(prefix_sort, value=p1_val)
        match_prefix = SMTMatchAttribute('prefix', prefix, sym_anns, ctx)

        pref = ctx.create_fresh_var(z3.IntSort(), value=100)
        match_pref = SMTMatchAttribute('local_pref', pref, sym_anns, ctx)
        matches = [match_prefix, match_pref]
        # Act
        match = SMTMatchAnd(matches, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)

        p1_val = prefix_sort.get_symbolic_value('Prefix1')
        prefix = ctx.create_fresh_var(prefix_sort)
        match_prefix = SMTMatchAttribute('prefix', prefix, sym_anns, ctx)

        pref = ctx.create_fresh_var(z3.IntSort())
        match_pref = SMTMatchAttribute('local_pref', pref, sym_anns, ctx)
        matches = [match_prefix, match_pref]
        # Act
        match = SMTMatchAnd(matches, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.add(const)
        solver.add(match.is_match(sym_anns[0]).var == True)
        solver.add(match.is_match(sym_anns[1]).var == False)
        is_sat = ctx.check(solver)
        print solver.to_smt2()
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(match_prefix.value.get_value(), 'Prefix1')
        self.assertEquals(match_pref.value.get_value(), 100)


@attr(speed='fast')
class TestSMTMatchOr(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)

        p1_val = prefix_sort.get_symbolic_value('Prefix1')
        prefix = ctx.create_fresh_var(prefix_sort, value=p1_val)
        match_prefix = SMTMatchAttribute('prefix', prefix, sym_anns, ctx)

        pref = ctx.create_fresh_var(z3.IntSort(), value=110)
        match_pref = SMTMatchAttribute('local_pref', pref, sym_anns, ctx)
        matches = [match_prefix, match_pref]
        # Act
        match = SMTMatchOr(matches, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertTrue(match.is_match(sym_anns[1]).get_value())

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)

        p1_val = prefix_sort.get_symbolic_value('Prefix1')
        prefix = ctx.create_fresh_var(prefix_sort)
        match_prefix = SMTMatchAttribute('prefix', prefix, sym_anns, ctx)

        pref = ctx.create_fresh_var(z3.IntSort())
        match_pref = SMTMatchAttribute('local_pref', pref, sym_anns, ctx)
        matches = [match_prefix, match_pref]
        # Act
        match = SMTMatchOr(matches, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.add(const)
        solver.add(match.is_match(sym_anns[0]).var == True)
        solver.add(match.is_match(sym_anns[1]).var == True)
        is_sat = ctx.check(solver)
        print solver.to_smt2()
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        values = [match_prefix.value.get_value(), match_pref.value.get_value()]
        v1 = [concrete_anns[0].prefix, concrete_anns[1].local_pref]
        v2 = [concrete_anns[1].prefix, concrete_anns[0].local_pref]
        self.assertTrue(values == v1 or values == v2)


@attr(speed='fast')
class TestSMTMatchPrefix(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)
        # Provide concrete value for the match
        p1_val = prefix_sort.get_symbolic_value('Prefix1')
        p1_sym = ctx.create_fresh_var(prefix_sort, value=p1_val)
        # Act
        match = SMTMatchPrefix(p1_sym, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)
        p1_sym = ctx.create_fresh_var(prefix_sort)
        # Act
        match = SMTMatchAttribute('prefix', p1_sym, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(p1_sym.get_value(), concrete_anns[0].prefix)
        self.assertNotEquals(p1_sym.get_value(), concrete_anns[1].prefix)


@attr(speed='fast')
class TestSMTMatchPeer(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        peer_sort = ctx.get_enum_type(PEER_SORT)
        # Provide concrete value for the match
        p1_val = peer_sort.get_symbolic_value('Peer1')
        p1_sym = ctx.create_fresh_var(peer_sort, value=p1_val)
        # Act
        match = SMTMatchPeer(p1_sym, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        peer_sort = ctx.get_enum_type(PEER_SORT)
        p1_sym = ctx.create_fresh_var(peer_sort)
        # Act
        match = SMTMatchPeer(p1_sym, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(p1_sym.get_value(), concrete_anns[0].peer)
        self.assertNotEquals(p1_sym.get_value(), concrete_anns[1].peer)


@attr(speed='fast')
class TestSMTMatchMED(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=20,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = z3.IntSort()
        # Provide concrete value for the match
        val = concrete_anns[0].med
        sym = ctx.create_fresh_var(vsort, value=val)
        # Act
        match = SMTMatchMED(sym, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertTrue(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        match = SMTMatchMED(None, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(match.value.get_value(), concrete_anns[0].med)
        self.assertNotEquals(match.value.get_value(), concrete_anns[1].med)


@attr(speed='fast')
class TestSMTMatchNextHop(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = ctx.get_enum_type(NEXT_HOP_SORT)
        # Provide concrete value for the match
        val = vsort.get_symbolic_value('Hop1')
        sym = ctx.create_fresh_var(vsort, value=val)
        # Act
        match = SMTMatchNextHop(sym, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())
        self.assertEquals(match.get_config(), MatchNextHop(concrete_anns[0].next_hop))

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        match = SMTMatchNextHop(None, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(match.value.get_value(), concrete_anns[0].next_hop)
        self.assertNotEquals(match.value.get_value(), concrete_anns[1].next_hop)
        self.assertEquals(match.get_config(), MatchNextHop(concrete_anns[0].next_hop))


@attr(speed='fast')
class TestSMTMatchAsPath(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = ctx.get_enum_type(ASPATH_SORT)
        # Provide concrete value for the match
        as_path = get_as_path_key([1, 2, 5, 7, 6])
        val = vsort.get_symbolic_value(as_path)
        sym = ctx.create_fresh_var(vsort, value=val)
        # Act
        match = SMTMatchASPath(sym, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())
        self.assertEquals(match.get_config(), MatchAsPath(concrete_anns[0].as_path))

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = ctx.get_enum_type(ASPATH_SORT)
        as_path = get_as_path_key([1, 2, 5, 7, 6])
        sym = ctx.create_fresh_var(vsort)
        # Act
        match = SMTMatchASPath(sym, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(sym.get_value(), as_path)
        self.assertEquals(match.get_config(), MatchAsPath(concrete_anns[0].as_path))


@attr(speed='fast')
class TestSMTMatchAsPathLen(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = z3.IntSort()
        # Provide concrete value for the match
        val = concrete_anns[0].as_path_len
        sym = ctx.create_fresh_var(vsort, value=val)
        # Act
        match = SMTMatchASPathLen(sym, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertTrue(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())
        self.assertEquals(match.get_config(), MatchAsPathLen(len(concrete_anns[0].as_path)))

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = z3.IntSort()
        sym = ctx.create_fresh_var(vsort)
        # Act
        match = SMTMatchASPathLen(sym, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(sym.get_value(), concrete_anns[0].as_path_len)
        self.assertEquals(match.get_config(), MatchAsPathLen(len(concrete_anns[0].as_path)))


@attr(speed='fast')
class TestSMTMatchPermitted(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=False)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = z3.BoolSort()
        # Provide concrete value for the match
        val = concrete_anns[0].permitted
        sym = ctx.create_fresh_var(vsort, value=val)
        # Act
        match = SMTMatchPermitted(sym, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertTrue(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = z3.BoolSort()
        sym = ctx.create_fresh_var(vsort)
        # Act
        match = SMTMatchPermitted(sym, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(sym.get_value(), concrete_anns[0].permitted)

@attr(speed='fast')
class TestSMTMatchOrigin(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.IGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = ctx.get_enum_type(BGP_ORIGIN_SORT)
        # Provide concrete value for the match
        val = vsort.get_symbolic_value('EBGP')
        sym = ctx.create_fresh_var(vsort, value=val)
        # Act
        match = SMTMatchOrigin(sym, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        vsort = ctx.get_enum_type(BGP_ORIGIN_SORT)
        sym = ctx.create_fresh_var(vsort)
        # Act
        match = SMTMatchOrigin(sym, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(sym.get_value(), 'EBGP')


@attr(speed='fast')
class TestSMTMatchSelectOne(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")
        self.communities = [c1, c2, c3]

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: False, c2: True, c3: True}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=100, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        match = SMTMatchSelectOne(sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        solver.add(match.is_match(sym_anns[0]).var == True)
        solver.add(match.is_match(sym_anns[1]).var == False)
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())
        self.assertIsNotNone(match.get_used_match())
        self.assertIsNotNone(match.get_used_match().get_config())

    def test_unsat(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        c2_match = SMTMatchCommunity(self.communities[0], None, sym_anns, ctx)
        lpref_match = SMTMatchLocalPref(None, sym_anns, ctx)
        # Act
        match = SMTMatchSelectOne(sym_anns, ctx, matches=[c2_match, lpref_match])
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete

        # Evaluate constraints
        solver = z3.Solver()
        solver.add(match.is_match(sym_anns[0]).var == True)
        solver.add(match.is_match(sym_anns[1]).var == False)
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.unsat)

    def test_only_one(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        c1_match = SMTMatchCommunity(self.communities[1], None, sym_anns, ctx)
        lpref_match = SMTMatchLocalPref(None, sym_anns, ctx)
        # Act
        match = SMTMatchSelectOne(sym_anns, ctx, matches=[c1_match, lpref_match])
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete

        # Evaluate constraints
        solver = z3.Solver()
        solver.add(match.is_match(sym_anns[0]).var == True)
        solver.add(match.is_match(sym_anns[1]).var == False)
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEqual(match.get_used_match(), c1_match)
        self.assertEqual(match.get_used_match().get_config(), self.communities[1])


@attr(speed='fast')
class TestAction(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        pref = ctx.create_fresh_var(z3.IntSort(), value=200)
        # Act
        action = SMTSetAttribute(match, 'local_pref', pref, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].local_pref.get_value(), 200)
        self.assertEquals(new_anns[1].local_pref.get_value(), 200)

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        value = ctx.create_fresh_var(z3.IntSort())
        match = SMTMatchAll(ctx)
        # Act
        action = SMTSetAttribute(match, 'local_pref', value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].local_pref.var == 200)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(value.get_value(), 200)
        self.assertEquals(new_anns[0].local_pref.get_value(), 200)
        self.assertEquals(new_anns[1].local_pref.get_value(), 200)

    def test_enum_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)
        sym_val = prefix_sort.get_symbolic_value('Prefix1')
        p1_sym = ctx.create_fresh_var(prefix_sort, value=sym_val)
        # Act
        action = SMTSetAttribute(match, 'prefix', p1_sym, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].prefix.get_value(), 'Prefix1')
        self.assertEquals(new_anns[1].prefix.get_value(), 'Prefix1')

    def test_enum_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        prefix_sort = ctx.get_enum_type(PREFIX_SORT)
        sym_val = prefix_sort.get_symbolic_value('Prefix1')
        p1_sym = ctx.create_fresh_var(prefix_sort)
        # Act
        action = SMTSetAttribute(match, 'prefix', p1_sym, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].prefix.var == sym_val)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].prefix.get_value(), 'Prefix1')
        self.assertEquals(new_anns[1].prefix.get_value(), 'Prefix1')


@attr(speed='fast')
class TestSMTSetLocalPref(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        local_pref = 200
        pref = ctx.create_fresh_var(z3.IntSort(), value=local_pref)
        # Act
        action = SMTSetLocalPref(match, pref, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].local_pref.get_value(), local_pref)
        self.assertEquals(new_anns[1].local_pref.get_value(), local_pref)
        self.assertEquals(action.get_config(), ActionSetLocalPref(local_pref))

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        local_pref = 200
        # Act
        action = SMTSetLocalPref(match, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].local_pref.var == local_pref)
        #solver.add(new_anns[0].local_pref.var == local_pref)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), local_pref)
        self.assertEquals(new_anns[0].local_pref.get_value(), local_pref)
        self.assertEquals(new_anns[1].local_pref.get_value(), local_pref)
        self.assertEquals(action.get_config(), ActionSetLocalPref(local_pref))


@attr(speed='fast')
class TestSMTSetPrefix(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = ctx.get_enum_type(PREFIX_SORT)
        value = ctx.create_fresh_var(vsort, value=concrete_anns[0].prefix)
        prefix = 'Prefix1'
        # Act
        action = SMTSetPrefix(match, value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].prefix.get_value(), prefix)
        self.assertEquals(new_anns[1].prefix.get_value(), prefix)
        self.assertEquals(action.get_config(), ActionSetPrefix(prefix))

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        prefix = 'Prefix1'
        # Act
        action = SMTSetPrefix(match, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].prefix.var == sym_anns[0].prefix.var)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), prefix)
        self.assertEquals(new_anns[0].prefix.get_value(), prefix)
        self.assertEquals(new_anns[1].prefix.get_value(), prefix)
        self.assertEquals(action.get_config(), ActionSetPrefix(prefix))


@attr(speed='fast')
class TestSMTSetPeer(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = ctx.get_enum_type(PEER_SORT)
        value = ctx.create_fresh_var(vsort, value=concrete_anns[0].peer)
        peer = 'Peer1'
        # Act
        action = SMTSetPeer(match, value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].peer.get_value(), peer)
        self.assertEquals(new_anns[1].peer.get_value(), peer)
        self.assertEquals(action.get_config(), ActionSetPeer(peer))

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        peer = 'Peer1'
        # Act
        action = SMTSetPeer(match, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].peer.var == sym_anns[0].peer.var)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), peer)
        self.assertEquals(new_anns[0].peer.get_value(), peer)
        self.assertEquals(new_anns[1].peer.get_value(), peer)
        self.assertEquals(action.get_config(), ActionSetPeer(peer))


@attr(speed='fast')
class TestSMTSetOrigin(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.IGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = ctx.get_enum_type(BGP_ORIGIN_SORT)
        value = ctx.create_fresh_var(vsort, value='EBGP')
        # Act
        action = SMTSetOrigin(match, value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].origin.get_value(), 'EBGP')
        self.assertEquals(new_anns[1].origin.get_value(), 'EBGP')

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        # Act
        action = SMTSetOrigin(match, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].origin.var == sym_anns[0].origin.var)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), 'EBGP')
        self.assertEquals(new_anns[0].origin.get_value(), 'EBGP')
        self.assertEquals(new_anns[1].origin.get_value(), 'EBGP')


@attr(speed='fast')
class TestSMTSetPermitted(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.IGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = z3.BoolSort()
        value = ctx.create_fresh_var(vsort, value=False)
        # Act
        action = SMTSetPermitted(match, value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].permitted.get_value(), False)
        self.assertEquals(new_anns[1].permitted.get_value(), False)

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        # Act
        action = SMTSetPermitted(match, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].permitted.var == False)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), False)
        self.assertEquals(new_anns[0].permitted.get_value(), False)
        self.assertEquals(new_anns[1].permitted.get_value(), False)


@attr(speed='fast')
class TestSMTSetASPath(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.IGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = ctx.get_enum_type(ASPATH_SORT)
        as_path = get_as_path_key(concrete_anns[0].as_path)
        value = ctx.create_fresh_var(vsort, value=as_path)
        # Act
        action = SMTSetASPath(match, value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].as_path.get_value(), as_path)
        self.assertEquals(new_anns[1].as_path.get_value(), as_path)

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        as_path = get_as_path_key(concrete_anns[0].as_path)
        match = SMTMatchAll(ctx)
        # Act
        action = SMTSetASPath(match, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].as_path.var == sym_anns[0].as_path.var)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), as_path)
        self.assertEquals(new_anns[0].as_path.get_value(), as_path)
        self.assertEquals(new_anns[1].as_path.get_value(), as_path)


@attr(speed='fast')
class TestSMTSetASPathLen(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.IGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = z3.IntSort()
        value = ctx.create_fresh_var(vsort, value=10)
        # Act
        action = SMTSetASPathLen(match, value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].as_path_len.get_value(), 10)
        self.assertEquals(new_anns[1].as_path_len.get_value(), 10)

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        # Act
        action = SMTSetASPathLen(match, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].as_path_len.var == 10)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), 10)
        self.assertEquals(new_anns[0].as_path_len.get_value(), 10)
        self.assertEquals(new_anns[1].as_path_len.get_value(), 10)


@attr(speed='fast')
class TestSMTSetNextHop(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.IGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = ctx.get_enum_type(NEXT_HOP_SORT)
        next_hop = concrete_anns[0].next_hop
        value = ctx.create_fresh_var(vsort, value=next_hop)
        # Act
        action = SMTSetNextHop(match, value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].next_hop.get_value(), next_hop)
        self.assertEquals(new_anns[1].next_hop.get_value(), next_hop)
        self.assertEquals(action.get_config(), ActionSetNextHop(next_hop))

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        next_hop = concrete_anns[0].next_hop
        # Act
        action = SMTSetNextHop(match, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].next_hop.var == sym_anns[0].next_hop.var)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), next_hop)
        self.assertEquals(new_anns[0].next_hop.get_value(), next_hop)
        self.assertEquals(new_anns[1].next_hop.get_value(), next_hop)
        self.assertEquals(action.get_config(), ActionSetNextHop(next_hop))


@attr(speed='fast')
class TestSMTSetMED(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.IGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_int_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = z3.IntSort()
        value = ctx.create_fresh_var(vsort, value=100)
        # Act
        action = SMTSetMED(match, value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].med.get_value(), 100)
        self.assertEquals(new_anns[1].med.get_value(), 100)

    def test_int_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        # Act
        action = SMTSetMED(match, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].med.var == 100)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), 100)
        self.assertEquals(new_anns[0].med.get_value(), 100)
        self.assertEquals(new_anns[1].med.get_value(), 100)


@attr(speed='fast')
class TestSMTSetOne(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")
        self.communities = [c1, c2, c3]

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.IGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = z3.IntSort()
        local_pref = ctx.create_fresh_var(vsort, value=200)
        med = ctx.create_fresh_var(vsort, value=300)
        action1 = SMTSetLocalPref(match, local_pref, sym_anns, ctx)
        action2 = SMTSetMED(match, med, sym_anns, ctx)
        # Act
        action = SMTSetOne(match, sym_anns, ctx, actions=[action1, action2])
        action.execute()
        new_anns = action.announcements
        solver = z3.Solver()
        solver.add(new_anns[0].med.var == med.get_value())
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat, solver.unsat_core())
        ctx.set_model(solver.model())
        self.assertEquals(action.get_used_action(), action2)
        self.assertEquals(new_anns[0].local_pref.get_value(), concrete_anns[0].local_pref)
        self.assertEquals(new_anns[1].local_pref.get_value(), concrete_anns[1].local_pref)
        self.assertEquals(new_anns[0].med.get_value(), med.get_value())
        self.assertEquals(new_anns[1].med.get_value(), med.get_value())

    def test_concrete_community(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = z3.IntSort()
        local_pref = ctx.create_fresh_var(vsort, value=200)
        med = ctx.create_fresh_var(vsort, value=300)
        set_pref = SMTSetLocalPref(match, local_pref, sym_anns, ctx)
        set_med = SMTSetMED(match, med, sym_anns, ctx)
        comm = self.communities[0]
        set_comm = SMTSetCommunity(match, comm, None, sym_anns, ctx)
        # Act
        action = SMTSetOne(match, sym_anns, ctx, actions=[set_pref, set_med, set_comm])
        action.execute()
        new_anns = action.announcements
        solver = z3.Solver()
        solver.add(new_anns[0].communities[comm].var == True)
        solver.add(new_anns[1].communities[comm].var == True)
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat, solver.unsat_core())
        ctx.set_model(solver.model())
        self.assertEquals(action.get_used_action(), set_comm)
        self.assertEquals(new_anns[0].communities[comm].get_value(), set_comm.value.get_value())
        self.assertEquals(new_anns[1].communities[comm].get_value(), set_comm.value.get_value())
        self.assertEquals(new_anns[0].local_pref.get_value(), concrete_anns[0].local_pref)
        self.assertEquals(new_anns[1].local_pref.get_value(), concrete_anns[1].local_pref)
        self.assertEquals(new_anns[0].med.get_value(), concrete_anns[0].med)
        self.assertEquals(new_anns[1].med.get_value(), concrete_anns[1].med)

    def test_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        med = 300
        # Act
        action = SMTSetOne(match, sym_anns, ctx)
        action.execute()
        new_anns = action.announcements
        solver = z3.Solver()
        solver.add(new_anns[0].med.var == med)
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat, solver.unsat_core())
        ctx.set_model(solver.model())
        action = action.get_used_action()
        self.assertIsInstance(action, SMTSetMED)
        self.assertEquals(new_anns[0].local_pref.get_value(), concrete_anns[0].local_pref)
        self.assertEquals(new_anns[1].local_pref.get_value(), concrete_anns[1].local_pref)
        self.assertEquals(action.value.get_value(), med)
        self.assertEquals(new_anns[0].med.get_value(), action.value.get_value())
        self.assertEquals(new_anns[1].med.get_value(), action.value.get_value())

    def test_sym_community(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        vsort = z3.IntSort()
        local_pref = ctx.create_fresh_var(vsort, value=200)
        comm = self.communities[0]
        # Act
        action = SMTSetOne(match, sym_anns, ctx)
        #action.execute()
        new_anns = action.announcements
        solver = z3.Solver()
        solver.add(new_anns[0].communities[comm].var == True)
        solver.add(new_anns[1].communities[comm].var == True)
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat, solver.unsat_core())
        ctx.set_model(solver.model())
        self.assertIsInstance(action.get_used_action(), SMTSetCommunity)
        set_comm = action.get_used_action()
        self.assertEquals(new_anns[0].communities[comm].get_value(), set_comm.value.get_value())
        self.assertEquals(new_anns[1].communities[comm].get_value(), set_comm.value.get_value())
        self.assertEquals(new_anns[0].local_pref.get_value(), concrete_anns[0].local_pref)
        self.assertEquals(new_anns[1].local_pref.get_value(), concrete_anns[1].local_pref)
        self.assertEquals(new_anns[0].med.get_value(), concrete_anns[0].med)
        self.assertEquals(new_anns[1].med.get_value(), concrete_anns[1].med)


@attr(speed='fast')
class TestSMTSetCommunity(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")
        self.communities = [c1, c2, c3]

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_concrete(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        community = self.communities[0]
        match = SMTMatchAll(ctx)
        # Act
        action = SMTSetCommunity(match, community, None, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].communities[community].get_value(), True)
        self.assertEquals(new_anns[1].communities[community].get_value(), True)
        self.assertEquals(action.get_config(), community)

    def test_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = SMTMatchAll(ctx)
        community = self.communities[0]
        value = ctx.create_fresh_var(z3.BoolSort())
        # Act
        action = SMTSetCommunity(match, community, value, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].communities[community].var == True)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.value.get_value(), True)
        self.assertEquals(new_anns[0].communities[community].get_value(), True)
        self.assertEquals(new_anns[1].communities[community].get_value(), True)
        self.assertEquals(action.get_config(), community)


@attr(speed='fast')
class TestSMTMatch(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: True}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)
        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_match_concrete_peer(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        r_match = MatchPeer('Peer1')
        match = SMTMatch(r_match, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym_peer(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        r_match = MatchPeer(VALUENOTSET)
        match = SMTMatch(r_match, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(match.value.get_value(), concrete_anns[0].peer)
        self.assertNotEquals(match.value.get_value(), concrete_anns[1].peer)

    def test_match_concrete_next_hop(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        r_match = MatchNextHop('Hop1')
        match = SMTMatch(r_match, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym_next_hop(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        r_match = MatchNextHop(VALUENOTSET)
        match = SMTMatch(r_match, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(match.value.get_value(), concrete_anns[0].next_hop)
        self.assertNotEquals(match.value.get_value(), concrete_anns[1].next_hop)

    def test_match_concrete_local_pref(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        r_match = MatchLocalPref(100)
        match = SMTMatch(r_match, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertTrue(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym_next_local_pref(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        r_match = MatchLocalPref(VALUENOTSET)
        match = SMTMatch(r_match, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(match.value.get_value(), concrete_anns[0].local_pref)
        self.assertNotEquals(match.value.get_value(), concrete_anns[1].local_pref)

    def test_match_concrete_comm_list(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        clist = CommunityList(
            list_id='clist1',
            access=Access.permit,
            communities=[Community("100:16"), Community("100:18")])
        # Act
        r_match = MatchCommunitiesList(clist)
        match = SMTMatch(r_match, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        ann0_value = match.is_match(sym_anns[0]).get_value()
        ann1_value = match.is_match(sym_anns[1]).get_value()
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertTrue(ann1_is_concrete)
        self.assertTrue(ann0_value)
        self.assertFalse(ann1_value)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym_comm_list(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        clist = CommunityList(
            list_id=1,
            access=Access.permit,
            communities=[VALUENOTSET, VALUENOTSET])
        # Act
        r_match = MatchCommunitiesList(clist)
        match = SMTMatch(r_match, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        comms = set([match.smt_match.matches[0].get_used_match().community, match.smt_match.matches[1].get_used_match().community])
        self.assertEquals(comms, set([Community("100:16"), Community("100:18")]))

    def test_match_concrete_ip_list(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        clist = IpPrefixList(
            name='iplist1',
            access=Access.permit,
            networks=['Prefix1'])
        # Act
        r_match = MatchIpPrefixListList(clist)
        match = SMTMatch(r_match, sym_anns, ctx)
        ann0_is_concrete = match.is_match(sym_anns[0]).is_concrete
        ann1_is_concrete = match.is_match(sym_anns[1]).is_concrete
        #ann0_value = match.is_match(sym_anns[0]).get_value()
        #ann1_value = match.is_match(sym_anns[1]).get_value()
        # Evaluate constraints
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertTrue(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match.is_match(sym_anns[0]).get_value())
        self.assertFalse(match.is_match(sym_anns[1]).get_value())

    def test_match_sym_ip_list(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        clist = IpPrefixList(
            name='iplist1',
            access=Access.permit,
            networks=[VALUENOTSET, VALUENOTSET])
        # Act
        r_match = MatchIpPrefixListList(clist)
        match = SMTMatch(r_match, sym_anns, ctx)
        match0 = match.is_match(sym_anns[0])
        match1 = match.is_match(sym_anns[1])
        ann0_is_concrete = match0.is_concrete
        ann1_is_concrete = match0.is_concrete
        # Evaluate constraints
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(match0.var == True)
        solver.add(match1.var == False)
        is_sat = ctx.check(solver)
        # Assert
        # Check the partial evaluation
        self.assertFalse(ann0_is_concrete)
        self.assertFalse(ann1_is_concrete)
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertTrue(match0.get_value())
        self.assertFalse(match1.get_value())
        self.assertEquals(match.smt_match.get_config(),
                          MatchIpPrefixListList(
                              IpPrefixList(
                                  name='iplist1',
                                  access=Access.permit,
                                  networks=['Prefix1'])))


@attr(speed='fast')
class TestSMTActions(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_concrete_next_hop(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        raction = ActionSetNextHop('Hop1')
        action = SMTActions(match, [raction], sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].next_hop.get_value(), 'Hop1')
        self.assertEquals(new_anns[1].next_hop.get_value(), 'Hop1')

    def test_sym_next_hop(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        raction = ActionSetNextHop(VALUENOTSET)
        action = SMTActions(match, [raction], sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].next_hop.var == sym_anns[0].next_hop.var)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.smt_actions[0].value.get_value(), 'Hop1')
        self.assertEquals(new_anns[0].next_hop.get_value(), 'Hop1')
        self.assertEquals(new_anns[1].next_hop.get_value(), 'Hop1')

    def test_concrete_local_pref(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        raction = ActionSetLocalPref(200)
        action = SMTActions(match, [raction], sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].local_pref.get_value(), 200)
        self.assertEquals(new_anns[1].local_pref.get_value(), 200)

    def test_sym_local_pref(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        raction = ActionSetLocalPref(VALUENOTSET)
        action = SMTActions(match, [raction], sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].local_pref.var == 200)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.smt_actions[0].value.get_value(), 200)
        self.assertEquals(new_anns[0].local_pref.get_value(), 200)
        self.assertEquals(new_anns[1].local_pref.get_value(), 200)

    def test_concrete_permitted(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        raction = ActionPermitted(Access.deny)
        action = SMTActions(match, [raction], sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].permitted.get_value(), False)
        self.assertEquals(new_anns[1].permitted.get_value(), False)

    def test_sym_local_permitted(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        raction = ActionPermitted(VALUENOTSET)
        action = SMTActions(match, [raction], sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].permitted.var == False)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.smt_actions[0].value.get_value(), False)
        self.assertEquals(new_anns[0].permitted.get_value(), False)
        self.assertEquals(new_anns[1].permitted.get_value(), False)

    def test_concrete_community(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        c = Community("100:16")
        raction = ActionSetCommunity([c], additive=True)
        action = SMTActions(match, [raction], sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].communities[c].get_value(), True)
        self.assertEquals(new_anns[1].communities[c].get_value(), True)
        self.assertEquals(action.get_config(), [raction])

    def test_sym_community(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        c = Community("100:16")
        raction = ActionSetCommunity([VALUENOTSET], additive=True)
        action = SMTActions(match, [raction], sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].communities[c].var == True)
        # FIXME: Check if one is enough!!!!
        solver.add(new_anns[1].communities[c].var == True)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.smt_actions[0].get_used_action().value.get_value(), True)
        self.assertEquals(new_anns[0].communities[c].get_value(), True)
        self.assertEquals(new_anns[1].communities[c].get_value(), True)
        self.assertEquals(action.get_config(), [ActionSetCommunity([c], additive=True)])


@attr(speed='fast')
class TestSMTRouteMapLine(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns)
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_concrete_next_hop(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)

        selectors = {}
        for announcement in sym_anns:
            index_var = ctx.create_fresh_var(z3.IntSort(), name_prefix='SS')
            selectors[announcement] = index_var
            ctx.register_constraint(index_var.var == 10, name_prefix='RmaplineIndex')

        # Act
        raction = ActionSetNextHop('Hop1')
        rline = RouteMapLine(matches=None, actions=[raction], access=Access.permit, lineno=10)
        action = SMTRouteMapLine(selectors, rline, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        #solver.add(new_anns[0].next_hop.var == sym_anns[0].next_hop.var)
        #solver.add(new_anns[1].next_hop.var == sym_anns[0].next_hop.var)
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].next_hop.get_value(), 'Hop1')
        self.assertEquals(new_anns[1].next_hop.get_value(), 'Hop1')
        self.assertEquals(action.get_config(), rline)

    def test_sym_next_hop(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)

        hop = 'Hop1'
        selectors = {}
        for announcement in sym_anns:
            index_var = ctx.create_fresh_var(z3.IntSort(), name_prefix='SS')
            selectors[announcement] = index_var
            ctx.register_constraint(index_var.var == 10, name_prefix='RmaplineIndex')
        # Act
        raction = ActionSetNextHop(VALUENOTSET)
        rline = RouteMapLine(matches=None, actions=[raction], access=Access.permit, lineno=10)
        action = SMTRouteMapLine(selectors, rline, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].next_hop.var == sym_anns[0].next_hop.var)
        solver.add(new_anns[1].next_hop.var == sym_anns[0].next_hop.var)
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.smt_actions.smt_actions[1].value.get_value(), hop)
        self.assertEquals(new_anns[0].next_hop.get_value(), hop)
        self.assertEquals(new_anns[1].next_hop.get_value(), hop)
        self.assertEquals(action.get_config(), RouteMapLine(matches=None, actions=[ActionSetNextHop(hop)], access=Access.permit, lineno=10))


@attr(speed='fast')
class TestSMTRouteMap(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=110, med=10,
            communities={c1: False, c2: False, c3: True}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns, next_hop_list=['Hop3', 'Hop4'])
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_concrete_next_hop(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        raction = ActionSetNextHop('Hop1')
        rline = RouteMapLine(matches=None, actions=[raction], access=Access.permit, lineno=10)
        rmap = RouteMap(name='r1', lines=[rline])
        action = SMTRouteMap(rmap, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(new_anns[0].next_hop.get_value(), 'Hop1')
        self.assertEquals(new_anns[1].next_hop.get_value(), 'Hop1')
        self.assertEquals(action.get_config(), rmap)

    def test_sym_next_hop(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match = None
        # Act
        raction = ActionSetNextHop(VALUENOTSET)
        rline = RouteMapLine(matches=None, actions=[raction], access=Access.permit, lineno=10)
        rmap = RouteMap(name='r1', lines=[rline])
        action = SMTRouteMap(rmap, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].next_hop.var == sym_anns[0].next_hop.vsort.get_symbolic_value('Hop1'))
        #solver.add(new_anns[1].next_hop.var == sym_anns[0].next_hop.vsort.get_symbolic_value('Hop1'))
        #solver.add(new_anns[0].local_pref.var == 200)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat)
        ctx.set_model(solver.model())
        self.assertEquals(action.smt_lines[0].smt_actions.smt_actions[1].value.get_value(), 'Hop1')
        self.assertEquals(new_anns[0].next_hop.get_value(), 'Hop1')
        self.assertEquals(new_anns[1].next_hop.get_value(), 'Hop1')

    def test_simple(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        raction1 = ActionSetLocalPref(200)
        raction2 = ActionSetLocalPref(300)
        match1 = MatchNextHop('Hop1')
        match2 = MatchNextHop('Hop2')
        rline1 = RouteMapLine(matches=[match1], actions=[raction1], access=Access.permit, lineno=10)
        rline2 = RouteMapLine(matches=[match2], actions=[raction2], access=Access.permit, lineno=20)
        rmap = RouteMap(name='r1', lines=[rline1, rline2])
        action = SMTRouteMap(rmap, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)
        solver.add(new_anns[0].local_pref.var == 200)
        #solver.add(new_anns[1].local_pref.var == 300)
        is_sat = ctx.check(solver)
        # Assert
        self.assertEquals(is_sat, z3.sat, solver.unsat_core())
        ctx.set_model(solver.model())

        self.assertEquals(new_anns[0].local_pref.get_value(), 200)
        self.assertEquals(new_anns[1].local_pref.get_value(), 300)
        self.assertEquals(action.get_config(), rmap)

    def test_two_lines(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        # Act
        raction1_1 = ActionSetLocalPref(200)
        raction1_2 = ActionSetNextHop('Hop3')
        raction2_1 = ActionSetLocalPref(300)
        raction2_2 = ActionSetNextHop('Hop4')
        c1 = Community("100:16")
        c3 = Community("100:18")
        match_c1 = MatchCommunitiesList(CommunityList(list_id=1, access=Access.permit, communities=[c1]))
        match_c3 = MatchCommunitiesList(CommunityList(list_id=1, access=Access.permit, communities=[c3]))
        rline1 = RouteMapLine(matches=[match_c1], actions=[raction1_1, raction1_2], access=Access.permit, lineno=10)
        rline2 = RouteMapLine(matches=[match_c3], actions=[raction2_1, raction2_2], access=Access.permit, lineno=20)
        rmap = RouteMap(name='r1', lines=[rline1, rline2])
        action = SMTRouteMap(rmap, sym_anns, ctx)
        new_anns = action.announcements
        solver = z3.Solver()
        for name, const in ctx.constraints_itr():
            solver.assert_and_track(const, name)

        #solver.add(new_anns[0].local_pref.var == 200)
        #solver.add(new_anns[1].local_pref.var == 300)

        is_sat = ctx.check(solver)
        print solver.to_smt2()
        # Assert
        if is_sat != z3.sat:
            print "Unsat core", solver.unsat_core()
        self.assertEquals(is_sat, z3.sat, solver.unsat_core())
        print solver.model()
        ctx.set_model(solver.model())

        self.assertEquals(new_anns[0].local_pref.get_value(), 200)
        self.assertEquals(new_anns[0].next_hop.get_value(), 'Hop3')

        self.assertEquals(new_anns[1].local_pref.get_value(), 300)
        self.assertEquals(new_anns[1].next_hop.get_value(), 'Hop4')
        self.assertEquals(action.get_config(), rmap)


@attr(speed='fast')
class TestSMTSelectorMatch(unittest.TestCase):
    def get_anns(self):
        c1 = Community("100:16")
        c2 = Community("100:17")
        c3 = Community("100:18")

        ann1 = Announcement(
            prefix='Prefix1', peer='Peer1', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[1, 2, 5, 7, 6], as_path_len=5,
            next_hop='Hop1', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: True}, permitted=True)

        ann2 = Announcement(
            prefix='Prefix2', peer='Peer2', origin=BGP_ATTRS_ORIGIN.EBGP,
            as_path=[9, 2, 5, 7, 8, 3, 10], as_path_len=7,
            next_hop='Hop2', local_pref=100, med=10,
            communities={c1: True, c2: False, c3: False}, permitted=True)

        return ann1, ann2

    def get_ctx(self, concrete_anns):
        ctx = SolverContext.create_context(concrete_anns, next_hop_list=['Hop3', 'Hop4'])
        return ctx

    def get_sym(self, concrete_anns, ctx):
        return read_announcements(concrete_anns, ctx)

    def test_select(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match_all = SMTMatchAll(ctx)
        selector_var1 = ctx.create_fresh_var(z3.IntSort(), name='Selector1')
        selector_var2 = ctx.create_fresh_var(z3.IntSort(), name='Selector2')
        selectors = {}
        selectors[sym_anns[0]] = selector_var1
        selectors[sym_anns[1]] = selector_var2
        # Act
        select1 = SMTSelectorMatch(selectors, 10, match_all, sym_anns, ctx)
        select2 = SMTSelectorMatch(selectors, 20, match_all, sym_anns, ctx)
        solver = z3.Solver()
        solver.add(select1.is_match(sym_anns[0]).var == True)
        solver.add(select2.is_match(sym_anns[0]).var == False)
        solver.add(select1.is_match(sym_anns[1]).var == False)
        solver.add(select2.is_match(sym_anns[1]).var == True)
        is_sat = ctx.check(solver)
        assert is_sat == z3.sat, solver.unsat_core()

    def test_select_sym(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match1 = SMTMatch(MatchNextHop(VALUENOTSET), sym_anns, ctx)
        match2 = SMTMatch(MatchNextHop(VALUENOTSET), sym_anns, ctx)
        selector_var1 = ctx.create_fresh_var(z3.IntSort(), name='Selector1')
        selector_var2 = ctx.create_fresh_var(z3.IntSort(), name='Selector2')
        selectors = {}
        selectors[sym_anns[0]] = selector_var1
        selectors[sym_anns[1]] = selector_var2
        # Act
        select1 = SMTSelectorMatch(selectors, 10, match1, sym_anns, ctx)
        select2 = SMTSelectorMatch(selectors, 20, match2, sym_anns, ctx)
        solver = z3.Solver()
        solver.add(select1.is_match(sym_anns[0]).var == True)
        solver.add(select2.is_match(sym_anns[0]).var == False)
        solver.add(select1.is_match(sym_anns[1]).var == False)
        solver.add(select2.is_match(sym_anns[1]).var == True)
        is_sat = ctx.check(solver)
        print solver.to_smt2()
        self.assertEquals(is_sat, z3.sat, solver.unsat_core())
        print "MATCH 1 val", match1.value
        print "MATCH 2 val", match2.value
        print "NEXT HOP1", sym_anns[0].next_hop
        print "NEXT HOP2", sym_anns[1].next_hop
        print "MATCH1 ann1 var", match1.is_match(sym_anns[0])
        print "MATCH1 ann2 var", match1.is_match(sym_anns[1])
        print "MATCH2 ann1 var", match2.is_match(sym_anns[0])
        print "MATCH2 ann2 var", match2.is_match(sym_anns[1])
        print solver.model()

        self.assertNotEquals(match1.get_config(), match2.get_config())

    def test_select_first(self):
        # Arrange
        concrete_anns = self.get_anns()
        ctx = self.get_ctx(concrete_anns)
        sym_anns = self.get_sym(concrete_anns, ctx)
        match1 = SMTMatch(MatchLocalPref(100), sym_anns, ctx)
        match2 = SMTMatch(MatchLocalPref(100), sym_anns, ctx)
        selector_var1 = ctx.create_fresh_var(z3.IntSort(), name='Selector1')
        selector_var2 = ctx.create_fresh_var(z3.IntSort(), name='Selector2')
        selectors = {}
        selectors[sym_anns[0]] = selector_var1
        selectors[sym_anns[1]] = selector_var2
        # Act
        select1 = SMTSelectorMatch(selectors, 10, match1, sym_anns, ctx)
        select2 = SMTSelectorMatch(selectors, 20, match2, sym_anns, ctx)
        solver = z3.Solver()
        solver.add(select1.is_match(sym_anns[0]).var == True)
        solver.add(select1.is_match(sym_anns[1]).var == True)
        solver.add(select2.is_match(sym_anns[0]).var == False)
        solver.add(select2.is_match(sym_anns[1]).var == False)

        is_sat = ctx.check(solver)
        print solver.to_smt2()
        self.assertEquals(is_sat, z3.sat, solver.unsat_core())
        print "MATCH 1 val", match1.value
        print "MATCH 2 val", match2.value
        print "NEXT HOP1", sym_anns[0].next_hop
        print "NEXT HOP2", sym_anns[1].next_hop
        print "MATCH1 ann1 var", match1.is_match(sym_anns[0])
        print "MATCH1 ann2 var", match1.is_match(sym_anns[1])
        print "MATCH2 ann1 var", match2.is_match(sym_anns[0])
        print "MATCH2 ann2 var", match2.is_match(sym_anns[1])
        print solver.model()

        self.assertIn(selector_var1.get_value(), [10, 20])
        self.assertIn(selector_var2.get_value(), [10, 20])
        self.assertEquals(match1.get_config(), match2.get_config())
