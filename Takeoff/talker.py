#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from my_py_pkg.action import Takeoff
from geometry_msgs.msg import PoseStamped
from mavros_msgs.srv import CommandBool, SetMode
from math import sqrt
import asyncio
import time

class takeoff_node(Node):
    def __init__(self):
        super().__init__('takeoff_server_node')
        self._action_server= ActionServer(self, Takeoff, 'takeoff_action', self.execute_callback)
        self.pose_publisher = self.create_publisher(PoseStamped, '/mavros/setpoints_position/local', 10)
        self.pose_subscriber = self.create_subscription(PoseStamped, 'mavros/local_position/pose', self.pose_cb, 10)
        self.arming_client = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.setmode_client = self.create_client(SetMode, '/mavros/set_mode')
        self.current_pose = None
    def pose_cb(self, msg):
        self.current_pose = msg
    async def execute_callback(self, goal_handle):
        goal= goal_handle.request.height
        self.get_logger().info(f"Takeoff goal: {goal} m")
        pose = PoseStamped()
        pose.pose.position.x = 0.0
        pose.pose.position.y = 0.0
        pose.pose.position.z = goal
        pose.header.frame_id = 'map'
        for i in range(20):
            pose.header.stamp = self.get_clock().now().to_msg()
            self.pose_publisher.publish(pose)
        await asyncio.sleep(0.1)
        armed = await self.arm()
        if not armed:
            goal_handle.abort()
            result= Takeoff.Result()
            result.success= False
            return result
        Takeoff.Result(success=False)
        mode_set = await self.set_offboard()
        if not mode_set:
            goal_handle.abort()
            result= Takeoff.Result()
            result.success= False
            return result
        Takeoff.Result(success=False)
        feedback= Takeoff.Feedback()
        while rclpy.ok():
            if self.current_pose is None:
                await asyncio.sleep(0.1)
                continue
            cur_z = self.current_pose.pose.position.z
            distance = abs(goal - cur_z)
            feedback.current_height = cur_z
            goal_handle.publish_feedback(feedback)
            self.pose_publisher.publish(pose)
            if distance < 0.2:
                break
            await asyncio.sleep(0.1)
        goal_handle.succeed()
        result= Takeoff.Result()
        result.success= True
        self.get_logger().info('Taked off completed.')
        return result
    async def arm(self):
        if not self.arming_client.wait_for_service(timeout_sec= 5):
            self.get_logger().info('Error with connecting to arm server.')
        else:
            self.get_logger().info('Arming...')
            arm_req = CommandBool().Request()
            arm_req.value = True
            future = self.arming_client.call_async(arm_req)
            while not future.done():
            	await asyncio.sleep(0.1)
            result = future.result()
            return result.success
            self.get_logger().info('Arm request sent successfully.')
    async def set_offboard(self):
        if not self.setmode_client.wait_for_service(timeout_sec=5):
            self.get_logger().info('Setting mode to offset...')
            mode_req = SetMode().Request()
            mode_req.custom_mode = 'OFFBOARD'
            future = self.setmode_client.call_async(mode_req)
            while not future.done():
            	await asyncio.sleep(0.1)
            result = future.result()
            return result.success
            self.get_logger().info('Set mode request sent successfully.')
def main(args = None):
    rclpy.init(args=args)
    client = LandClient()
    client.send_goal()
    time.sleep()
    client.destroy_node()
    rclpy.shutdown()
if __name__=='__main__':
    main()
