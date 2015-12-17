import unittest
import os
import cPickle
from mock import patch, call
from examples.gnr.node import parse_peer, start
from click.testing import CliRunner
from golem.network.transport.tcpnetwork import TCPAddress


class TestParseConnect(unittest.TestCase):
    def test_parse_peer(self):
        addr = parse_peer(None, "connect", ("127.0.0.1:15", ))
        self.assertEqual(len(addr), 1)
        self.assertEqual(addr[0].address, "127.0.0.1")
        self.assertEqual(addr[0].port, 15)

        addr = parse_peer(None, "connect", ("127.0.0.2:30", "blargh"))
        self.assertEqual(len(addr), 1)
        self.assertEqual(addr[0].address, "127.0.0.2")
        self.assertEqual(addr[0].port, 30)

        addr = parse_peer(None, "connect", ("10.32.10.33:abc", "10.32.10.33:10", "abc:30"))
        self.assertEqual(len(addr), 2)
        self.assertEqual(addr[0].address, "10.32.10.33")
        self.assertEqual(addr[0].port, 10)
        self.assertEqual(addr[1].port, 30)

    def test_parse_peer_ip6(self):
        addr = parse_peer(None, "connect", ("10.30.12.13:45", "[::ffff:0:0:0]:96", "10.30.10.12:3013",
                          "[2001:db8:85a3:8d3:1319:8a2e:370:7348]:443"))
        self.assertEqual(len(addr), 4)
        self.assertEqual(addr[1].address, "::ffff:0:0:0")
        self.assertEqual(addr[1].port, 96)
        self.assertEqual(addr[2].address, "10.30.10.12")
        self.assertEqual(addr[2].port, 3013)
        self.assertEqual(addr[3].address, "2001:db8:85a3:8d3:1319:8a2e:370:7348")
        self.assertEqual(addr[3].port, 443)


class A(object):
    def __init__(self):
        self.a = 2
        self.b = "abc"


class TestNode(unittest.TestCase):

    @patch('examples.gnr.node.reactor')
    def test_help(self, mock_reactor):
        runner = CliRunner()
        return_value = runner.invoke(start, ['--help'])
        self.assertEqual(return_value.exit_code, 0)
        self.assertTrue(return_value.output.startswith('Usage'))
        mock_reactor.run.assert_not_called()

    @patch('examples.gnr.node.reactor')
    def test_wrong_option(self, mock_reactor):
        runner = CliRunner()
        return_value = runner.invoke(start, ['--blargh'])
        self.assertEqual(return_value.exit_code, 2)
        self.assertTrue(return_value.output.startswith('Error'))
        mock_reactor.run.assert_not_called()

    @patch('examples.gnr.node.GNRNode')
    def test_no_args(self, mock_node):
        runner = CliRunner()
        return_value = runner.invoke(start)
        self.assertEqual(return_value.exit_code, 0)
        mock_node.assert_has_calls([call().run()])

    @patch('examples.gnr.node.GNRNode')
    def test_wrong_peer_good_peer(self, mock_node):
        runner = CliRunner()
        return_value = runner.invoke(start, ['--peer', '10.30.10.216:40111', '--peer', 'bla'])
        self.assertEqual(return_value.exit_code, 0)
        mock_node.assert_has_calls([call().run(), call().add_tasks([])], any_order=True)
        call_names = [name for name, arg, kwarg in mock_node.mock_calls]
        self.assertTrue('().connect_with_peers' in call_names)
        peer_num = call_names.index('().connect_with_peers')
        peer_arg = mock_node.mock_calls[peer_num][1][0]
        self.assertEqual(len(peer_arg), 1)
        self.assertEqual(peer_arg[0], TCPAddress('10.30.10.216', 40111))

    @patch('examples.gnr.node.GNRNode')
    def test_peers(self, mock_node):
        runner = CliRunner()
        return_value = runner.invoke(start, ['--peer', '10.30.10.216:40111', '--peer',
                                                  '[2001:db8:85a3:8d3:1319:8a2e:370:7348]:443'])
        self.assertEqual(return_value.exit_code, 0)
        mock_node.assert_has_calls([call().run(), call().add_tasks([])], any_order=True)
        call_names = [name for name, arg, kwarg in mock_node.mock_calls]
        self.assertTrue('().connect_with_peers' in call_names)
        peer_num = call_names.index('().connect_with_peers')
        peer_arg = mock_node.mock_calls[peer_num][1][0]
        self.assertEqual(len(peer_arg), 2)
        self.assertEqual(peer_arg[0], TCPAddress('10.30.10.216', 40111))
        self.assertEqual(peer_arg[1], TCPAddress('2001:db8:85a3:8d3:1319:8a2e:370:7348', 443))

    @patch('examples.gnr.node.GNRNode')
    def test_wrong_task(self, mock_node):
        runner = CliRunner()
        return_value = runner.invoke(start, ['--task', 'testtask.gt'])
        self.assertEqual(return_value.exit_code, 2)
        self.assertTrue('Error' in return_value.output and 'Usage' in return_value.output)

    @patch('examples.gnr.node.GNRNode')
    def test_task(self, mock_node):
        runner = CliRunner()

        a = A()
        with open('testclassdump', 'w') as f:
            cPickle.dump(a, f)
        return_value = runner.invoke(start, ['--task', 'testclassdump', '--task', 'testclassdump'])
        self.assertEqual(return_value.exit_code, 0)
        mock_node.assert_has_calls([call().run()])
        call_names = [name for name, arg, kwarg in mock_node.mock_calls]
        self.assertTrue('().add_tasks' in call_names)
        task_num = call_names.index('().add_tasks')
        task_arg = mock_node.mock_calls[task_num][1][0]
        self.assertEqual(len(task_arg), 2)
        self.assertIsInstance(task_arg[0], A)
        if os.path.exists('testclassdump'):
            os.remove('testclassdump')
