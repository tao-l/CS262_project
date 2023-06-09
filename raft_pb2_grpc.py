# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import raft_pb2 as raft__pb2


class RaftServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.rpc_append_entries = channel.unary_unary(
                '/raft.RaftService/rpc_append_entries',
                request_serializer=raft__pb2.AE_Request.SerializeToString,
                response_deserializer=raft__pb2.AE_Response.FromString,
                )
        self.rpc_request_vote = channel.unary_unary(
                '/raft.RaftService/rpc_request_vote',
                request_serializer=raft__pb2.RV_Request.SerializeToString,
                response_deserializer=raft__pb2.RV_Response.FromString,
                )


class RaftServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def rpc_append_entries(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def rpc_request_vote(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_RaftServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'rpc_append_entries': grpc.unary_unary_rpc_method_handler(
                    servicer.rpc_append_entries,
                    request_deserializer=raft__pb2.AE_Request.FromString,
                    response_serializer=raft__pb2.AE_Response.SerializeToString,
            ),
            'rpc_request_vote': grpc.unary_unary_rpc_method_handler(
                    servicer.rpc_request_vote,
                    request_deserializer=raft__pb2.RV_Request.FromString,
                    response_serializer=raft__pb2.RV_Response.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'raft.RaftService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class RaftService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def rpc_append_entries(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/raft.RaftService/rpc_append_entries',
            raft__pb2.AE_Request.SerializeToString,
            raft__pb2.AE_Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def rpc_request_vote(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/raft.RaftService/rpc_request_vote',
            raft__pb2.RV_Request.SerializeToString,
            raft__pb2.RV_Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
