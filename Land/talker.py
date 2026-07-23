#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from land.action import Land
from geometry_msgs.msg import PoseStamped
from mavros_msgs.srv import CommandBool
import asyncio

class land_server(Node):
    def __init__(self):
        super().__init__('land_server')
        self._node= ActionServer('land_action', Land, 'land_action', self.execute_callback)
        self.arm_client = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.pose_publisher = self.create_publisher(PoseStamped, '/mavros/setpoints_position/local', 10)
        self.pose_subscriber = self.create_subscription(PoseStamped, 'mavros/local_position/pose', self.pose_cb, 10)
        self.current_pose = None
    def pose_cb(self, msg):
        self.current_pose = msg
    async def execute_callback(self, goal_handle):
        self.get_logger().info(f"Landing from height: {current_height} m")
        pose = PoseStamped()
        pose.pose.position.x = 0
        pose.pose.position.y = 0
        pose.pose.position.z = 0
        pose.header.frame_id = 'map'
        for i in range(20):
            pose.header.stamp = self.get_clock().now().to_msg()
            self.pose_publisher.publish(pose)
        await asyncio.sleep(0.1)
        feedback= Land.Feedback()
        goal_handle.publish_feedback(feedback)
        while rclpy.ok():
            if self.current_pose is None:
                await asyncio.sleep(0.1)
                continue
            current_height= goal_handle.request.height
            if current_height < 0.2:
                self.arm()
            await asyncio.sleep(0.1)
        goal_handle.succeed()
        result = Land.Result()
        result.success = True
        self.get_logger().info('Landed successfully.')
    def arm(self):
        if not self.arm_client.wait_for_service(timeout_sec= 5):
            self.get_logger().info('Error with connecting to arm server.')
        else:
            arm_req = CommandBool().Request()
            arm_req.value = False
            future = self.arm_client.call_async(arm_req)
            while not future.done():
            	await asyncio.sleep(0.1)
            result = future.result()
            return result.success
            self.get_logger().info('Arm request sent successfully.')
def main(args = None):
    rclpy.init(args=args)
    client = LandClient()
    client.send_goal()
    time.sleep()
    client.destroy_node()
    rclpy.shutdown()
if __name__=='__main__':
    main()
