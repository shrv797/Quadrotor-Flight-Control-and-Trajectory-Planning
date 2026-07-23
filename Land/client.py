#!/usr/bin/env python3
import rclpy
from rclpy.action import ActionClient
from land.action import Land
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from mavros_msgs.srv import CommandBool, SetMode
import time

class LandClient(Node):
    def __init__(self):
        super().__init__('land_client')
        self._client = ActionClient(self, Land, 'land_action')
        self.pose_publisher = self.create_publisher(PoseStamped, '/mavros/setpoints_position/local', 10)
        self.set_mode_client = self.create_client(SetMode, '/mavros/set_mode')
        self.arm_client = self.create_client(CommandBool, '/mavros/cmd/arming')
    def send_goal(self):
        self.send_initial_points()
        self.set_mode()
        self.arm()
        self._client.wait_for_server()
        goal_msg = Land.Goal()
        goal_msg.height = 0
        self._send_goal_future = self._client.send_goal_async(goal_msg)
        self._send_goal_future.add_done_callback(self.callback_func)
    def send_initial_points(self):
        self.get_logger().info('Sending initial points...')
        pose = PoseStamped()
        pose.pose.position.x = 0
        pose.pose.position.y = 0
        pose.pose.position.z = 2.5
        pose.header.frame_id = 'map'
        for i in range(20):
            pose.header.stamp = self.get_clock().now().to_msg()
            self.pose_publisher.publish(pose)
        time.sleep(0.1)
    def set_mode(self):
        if not self.set_mode_client.wait_for_server(timeout_sec = 5):
            self.get_logger().info('Error with connecting to set mode server...')
        else:
            request = SetMode.Request()
            request.custom_mode = 'OFFBOARD'
            future = self.set_mode_client.call_async(request)
            while not future.done():
            	await asyncio.sleep(0.1)
            result = future.result()
            return result.success
            self.get_logger().info('Successfully seting the mode to offboard.')
    def arm(self):
        if not self.arm_client.wait_for_service(timeout_sec= 5):
            self.get_logger().info('Error with connecting to arming server...')
        else:
            request = CommandBool.Request()
            request.value = True
            future = self.arm_client.call_async(request)
            while not future.done():
            	await asyncio.sleep(0.1)
            result = future.result()
            return result.success
            if future.result().success:
                self.get_logger().info('Arming request sent successfully.')
            else:
                self.get_logger().info('Failed to arm.')
    def callback_func(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted():
            self.get_logger().info('Landing Failed.')
        elif not goal_handle.accepted:
            self.get_logger().info('Goal rejected.')
        else:
            self.get_logger().info('Goal accepted. wait for result...')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result)
    def get_result(self, future):
        result = future.result().result
        self.get_logger().info(f'Landing Result: {result.success}')
def main(args = None):
    rclpy.init(args=args)
    client = LandClient()
    client.send_goal()
    time.sleep()
    client.destroy_node()
    rclpy.shutdown()
if __name__=='__main__':
    main()
