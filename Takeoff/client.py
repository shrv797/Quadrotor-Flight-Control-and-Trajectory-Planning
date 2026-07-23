#!/usr/bin/env python3
import rclpy
from rclpy.action import ActionClient
from takeoff.action import Takeoff
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from mavros_msgs.srv import CommandBool, SetMode
import time

class takeoff_client(Node):
    def __init__(self):
        super().__init__('takeoff_client')
        self._takeoff_client = ActionClient(self, Takeoff, 'takeoff_action')
        self.pose_publisher = self.create_publisher(PoseStamped, '/mavros/setpoints_position/local', 10)
        self.arming_client = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.setmode_client = self.create_client(SetMode, '/mavros/set_mode')
    def send_goal(self, height = 2.5):
        self.send_initial_setpoint(height)
        self.arm()
        self.set_offboard()
        self._takeoff_client.wait_for_server()
        goal_msg = Takeoff.Goal()
        goal_msg.height = height
        self._send_goal = self._takeoff_client.send_goal_async(goal_msg)
        self._send_goal.add_done_callback(self.send_func)
    def send_initial_setpoint(self, height):
        self.get_logger().info('Sending initial setpoints for OFFBOARD mode...')
        pose = PoseStamped()
        pose.pose.position.x = 0
        pose.pose.position.y = 0
        pose.pose.position.z = height
        pose.header.frame_id = 'map'
        for i in range(20):
            pose.header.stamp = self.get_clock().now().to_msg()
            self.pose_publisher.publish(pose)
        rclpy.spin_once(self, timeout_sec=0.1)
    def arm(self):
        if not self.arming_client.wait_for_service(timeout_sec=5):
            self.get_logger().info('Error with connecting the arming service.')
        else:
            request = CommandBool.Request()
            request.value = True
            future = self.arming_client.call_async(request)
            while not future.done():
            	await asyncio.sleep(0.1)
            result = future.result()
            return result.success
            self.get_logger().info('Arming request sent successfully.')
    def set_offboard(self):
        if not self.setmode_client.wait_for_service(timeout_sec= 5):
            self.get_logger().info('Error with connecting the mode service.')
        else:
            request = SetMode.Request()
            request.custom_mode = 'OFFBOARD'
            future = self.setmode_client.call_async(request)
            while not future.done():
            	await asyncio.sleep(0.1)
            result = future.result()
            return result.success
            self.get_logger().info('Successfully seting the mode to offboard.')
    def send_func(self, future):
        get_result = future.result()
        if not get_result.accepted:
            self.get_logger().info('Taking off failed.')
        else:
            self.get_logger().info('Successfully taked off.')
        self._get_result_future = get_result.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_func)
    def get_result_func(self, future):
        get_result = future.result().result
        self.get_logger().info(f'Takeoff result: {get_result.success}')
        rclpy.shutdown()
def main(args = None):
    rclpy.init(args=args)
    client = LandClient()
    client.send_goal()
    time.sleep()
    client.destroy_node()
    rclpy.shutdown()
if __name__=='__main__':
    main()
