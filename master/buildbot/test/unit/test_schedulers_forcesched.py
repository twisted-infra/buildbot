# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

from twisted.trial import unittest
from twisted.internet import defer
from buildbot import config
from buildbot.schedulers.forcesched import ForceScheduler, StringParameter
from buildbot.schedulers.forcesched import IntParameter, FixedParameter
from buildbot.schedulers.forcesched import BooleanParameter, UserNameParameter
from buildbot.schedulers.forcesched import ChoiceStringParameter, ValidationError
from buildbot.test.util import scheduler

class TestForceScheduler(scheduler.SchedulerMixin, unittest.TestCase):

    OBJECTID = 19

    def setUp(self):
        self.setUpScheduler()

    def tearDown(self):
        self.tearDownScheduler()

    def makeScheduler(self, name='testsched', builderNames=['a', 'b'],
                            **kw):
        sched = self.attachScheduler(
                ForceScheduler(name=name, builderNames=builderNames,**kw),
                self.OBJECTID)
        sched.master.config = config.MasterConfig()
        return sched

    # tests

    def test_compare_branch(self):
        self.assertNotEqual(
                ForceScheduler(name="testched", builderNames=[]),
                ForceScheduler(name="testched", builderNames=[],
                    branch=FixedParameter("branch","fishing/pole")))


    def test_compare_reason(self):
        self.assertNotEqual(
                ForceScheduler(name="testched", builderNames=[],
                    reason=FixedParameter("reason","no fish for you!")),
                ForceScheduler(name="testched", builderNames=[],
                    reason=FixedParameter("reason","thanks for the fish!")))


    def test_compare_revision(self):
        self.assertNotEqual(
                ForceScheduler(name="testched", builderNames=[],
                    revision=FixedParameter("revision","fish-v1")),
                ForceScheduler(name="testched", builderNames=[],
                    revision=FixedParameter("revision","fish-v2")))


    def test_compare_repository(self):
        self.assertNotEqual(
                ForceScheduler(name="testched", builderNames=[],
                    repository=FixedParameter("repository","git://pond.org/fisher.git")),
                ForceScheduler(name="testched", builderNames=[],
                    repository=FixedParameter("repository","svn://ocean.com/trawler/")))


    def test_compare_project(self):
        self.assertNotEqual(
                ForceScheduler(name="testched", builderNames=[],
                    project=FixedParameter("project","fisher")),
                ForceScheduler(name="testched", builderNames=[],
                    project=FixedParameter("project","trawler")))


    def test_compare_username(self):
        self.assertNotEqual(
                ForceScheduler(name="testched", builderNames=[]),
                ForceScheduler(name="testched", builderNames=[],
                    project=FixedParameter("username","The Fisher King <avallach@atlantis.al>")))


    def test_compare_properties(self):
        self.assertNotEqual(
                ForceScheduler(name="testched", builderNames=[],
                    properties=[]),
                ForceScheduler(name="testched", builderNames=[],
                    properties=[FixedParameter("prop","thanks for the fish!")]))



    @defer.inlineCallbacks
    def test_basicForce(self):
        sched = self.makeScheduler()
        
        res = yield sched.force('user', 'a', branch='a', reason='because',revision='c',
                        repository='d', project='p',
                        property1name='p1',property1value='e',
                        property2name='p2',property2value='f',
                        property3name='p3',property3value='g',
                        property4name='p4',property4value='h'
                        )
        bsid,brids = res

        # only one builder forced, so there should only be one brid
        self.assertEqual(len(brids), 1)

        self.db.buildsets.assertBuildset\
            (bsid,
             dict(reason="A build was forced by 'user': because",
                  brids=brids,
                  external_idstring=None,
                  properties=[ ('owner', ('user', 'Force Build Form')),
                               ('p1', ('e', 'Force Build Form')),
                               ('p2', ('f', 'Force Build Form')),
                               ('p3', ('g', 'Force Build Form')),
                               ('p4', ('h', 'Force Build Form')),
                               ('reason', ('because', 'Force Build Form')),
                               ('scheduler', ('testsched', 'Scheduler')),
                               ],
                  sourcestampsetid=100),
             {'d':
              dict(branch='a', revision='c', repository='d',
                  project='p', sourcestampsetid=100)
             })

    @defer.inlineCallbacks
    def do_ParameterTest(self, value, expect, klass, owner='user', req=None,
                            **kwargs):
        sched = self.makeScheduler(properties=[klass(name="p1",**kwargs)])
        if not req:
            req = dict(p1=value, reason='because')
        try:
            bsid, brids = yield sched.force(owner, 'a', **req)
        except Exception,e:
            if not isinstance(e, expect):
                raise
            defer.returnValue(None) # success

        self.db.buildsets.assertBuildset\
            (bsid,
             dict(reason="A build was forced by 'user': because",
                  brids=brids,
                  external_idstring=None,
                  properties=[ 
                               ('owner', ('user', 'Force Build Form')),
                               ('p1', (expect, 'Force Build Form')),
                               ('reason', ('because', 'Force Build Form')),
                               ('scheduler', ('testsched', 'Scheduler')),
                               ],
                  sourcestampsetid=100),
             {"":
              dict(branch="", revision="", repository="",
                  project="", sourcestampsetid=100)
             })


    def test_StringParameter(self):
        self.do_ParameterTest(value="testedvalue", expect="testedvalue",
                                klass=StringParameter)

    def test_IntParameter(self):
        self.do_ParameterTest(value="123", expect=123, klass=IntParameter)


    def test_FixedParameter(self):
        self.do_ParameterTest(value="123", expect="321", klass=FixedParameter,
                default="321")


    def test_BooleanParameter_True(self):
        req = dict(p1=True,reason='because')
        self.do_ParameterTest(value="123", expect=True, klass=BooleanParameter,
                req=req)


    def test_BooleanParameter_False(self):
        req = dict(p2=True,reason='because')
        self.do_ParameterTest(value="123", expect=False,
                klass=BooleanParameter, req=req)


    def test_UserNameParameter(self):
        email = "test <test@buildbot.net>"
        self.do_ParameterTest(value=email, expect=email,
                klass=UserNameParameter)


    def test_UserNameParameterError(self):
        for value in ["test","test@buildbot.net","<test@buildbot.net>"]:
            self.do_ParameterTest(value=value, expect=ValidationError,
                    klass=UserNameParameter, debug=False)


    def test_ChoiceParameter(self):
        self.do_ParameterTest(value='t1', expect='t1',
                klass=ChoiceStringParameter, choices=['t1','t2'])


    def test_ChoiceParameterError(self):
        self.do_ParameterTest(value='t3', expect=ValidationError,
                klass=ChoiceStringParameter, choices=['t1','t2'],
                debug=False)


    def test_ChoiceParameterMultiple(self):
        self.do_ParameterTest(value=['t1','t2'], expect=['t1','t2'],
                klass=ChoiceStringParameter,choices=['t1','t2'], multiple=True)


    def test_ChoiceParameterMultipleError(self):
        self.do_ParameterTest(value=['t1','t3'], expect=ValidationError,
                klass=ChoiceStringParameter, choices=['t1','t2'],
                multiple=True, debug=False)
