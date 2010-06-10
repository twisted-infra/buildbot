import os
import shutil

from buildslave.test.fake import slavebuilder, runprocess
from buildslave.commands import utils
import buildslave.runprocess

class CommandTestMixin:
    """
    Support for testing Command subclasses.
    """

    def setUpCommand(self):
        """
        Get things ready to test a Command

        Sets:
            self.basedir -- the basedir
            self.basedir_workdir -- os.path.join(self.basedir, 'workdir')
        """
        self.basedir = 'basedir'
        self.basedir_workdir = os.path.join('basedir', 'workdir')

    def tearDownCommand(self):
        """
        Call this from the tearDown method to clean up any leftover workdirs and do
        any additional cleanup required.
        """
        # note: Twisted-2.5.0 does not have addCleanup, or we could use that here..
        if hasattr(self, 'makedirs') and self.makedirs:
            basedir_abs = os.path.abspath(os.path.join('basedir'))
            if os.path.exists(basedir_abs):
                shutil.rmtree(basedir_abs)

        # finish up the runprocess
        if hasattr(self, 'runprocess_patched') and self.runprocess_patched:
            runprocess.FakeRunProcess.test_done()

    def make_command(self, cmdclass, args, makedirs=False, patch_sourcedata_fns=False):
        """
        Create a new command object, creating the necessary arguments.  The
        cmdclass argument is the Command class, and args is the args dict
        to pass to its constructor.

        This always creates the SlaveBuilder with a basedir (self.basedir).  If
        makedirs is true, it will create the basedir and a workdir directory
        inside (named 'workdir').

        The resulting command is returned, but as a side-effect, the following
        attributes are set:

            self.cmd -- the command
            self.builder -- the (fake) SlaveBuilder

        If patch_sourcedata_fns is true, then the resulting command's
        writeSourceata and readSourcedata methods are patched to write and read
        self.sourcedata instead.
        """

        # set up the workdir and basedir
        self.makedirs = makedirs
        if makedirs:
            basedir_abs = os.path.abspath(os.path.join(self.basedir))
            workdir_abs = os.path.abspath(os.path.join(self.basedir, 'workdir'))
            if os.path.exists(basedir_abs):
                shutil.rmtree(basedir_abs)
            os.makedirs(workdir_abs)

        b = self.builder = slavebuilder.FakeSlaveBuilder(basedir=self.basedir)
        self.cmd = cmdclass(b, 'fake-stepid', args)

        if patch_sourcedata_fns:
            self.sourcedata = ''
            def readSourcedata():
                return self.sourcedata
            self.patch(self.cmd, 'readSourcedata', readSourcedata)
            def writeSourcedata(res):
                self.sourcedata = self.cmd.sourcedata
                return res
            self.patch(self.cmd, 'writeSourcedata', writeSourcedata)

        return self.cmd

    def run_command(self):
        """
        Run the command created by make_command.  Returns a deferred that will fire
        on success or failure.
        """
        return self.cmd.doStart()

    def get_updates(self):
        """
        Return the updates made so far
        """
        return self.builder.updates

    def patch_runprocess(self, *expectations):
        """
        Patch a fake RunProcess class in, and set the given expectations.
        """
        self.patch(buildslave.runprocess, 'RunProcess', runprocess.FakeRunProcess)
        buildslave.runprocess.RunProcess.expect(*expectations)
        self.runprocess_patched = True

    def patch_getCommand(self, name, result):
        """
        Patch utils.getCommand to return RESULT for NAME
        """
        old_getCommand = utils.getCommand
        def new_getCommand(n):
            if n == name: return result
            return old_getCommand(n)
        self.patch(utils, 'getCommand', new_getCommand)

    def clean_environ(self):
        """
        Temporarily clean out os.environ to { 'PWD' : '.' }
        """
        self.patch(os, 'environ', { 'PWD' : '.' })

    def check_sourcedata(self, _, expected_sourcedata):
        """
        Assert that the sourcedata (from the patched sourcedata_fns - see
        make_command) is correct.  Use this as a deferred callback.
        """
        self.assertEqual(self.sourcedata, expected_sourcedata)
        return _