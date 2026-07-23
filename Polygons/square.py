#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from mavros_msgs.srv import CommandBool, SetMode
from math import sin , cos , pi , sqrt

class Drawing(Node):
    def __init__(self):
        super().__init__('Drawing_Node')
        self.pose_publisher = self.create_publisher(PoseStamped, '/mavros/setpoint_position/local', 10)
        self.current_pose = None
        self.pose_subscriber = self.create_subscription(PoseStamped, '/mavros/local_position/pose',self.pose_cb, 10)
        self.arming_client = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.setmode_client = self.create_client(SetMode, '/mavros/set_mode')
        self.sides = 4
        self.radius = 3
        self.hieght = 2.5
        self.points = self.generate_polygon(self.sides, self.radius, self.hieght)
        self.current_index = 0
        self.flight_started = False
        self.timer = self.create_timer(0.1, self.timer_callback)
    def pose_cb(self, msg):
        self.current_pose = msg
    def generate_polygon(self, sides, radius, hieght):
        points = []
        for i in range(sides):
            angle = 2 * pi * radius / sides
            x = radius * cos(angle)
            y = radius * sin(angle)
            p = PoseStamped()
            p.pose.position.x = x
            p.pose.position.y = y
            p.pose.position.z = hieght
            p.header.frame_id = 'map'
            points.append(p)
        return points
    def timer_callback(self):
        if not self.flight_started:
            self.prepare_flight()
            return
        if self.current_pose is None:
            return
        target = self.points[self.current_index]
        self.publish_setpoints(target)
        if self.reached(target):
            self.get_logger().info(f'Reached the point {self.current_index +1} / {len(self.points)}')
            self.current_index += 1
            if self.current_index >= len(self.points) : 
                self.get_logger().info('Drawing completed!')
                rclpy.shutdown()
    def publish_setpoints(self, target):
        target.header.stamp = self.get_clock().now().to_msg()
        self.pose_publisher(target)
    def reached(self, target, telorance = 0.3):
        current = self.current_pose.pose.position
        tgt = target.pose.position
        distance = sqrt(((tgt.x - current.x)**2) + ((tgt.y - current.y)**2) + ((tgt.z - current.z)**2))
        return distance < telorance
    def prepare_flight(self):
        self.get_logger().info('Preparing for flight...')
        for i in range(20):
            self.publish_setpoints(self.points[0])
            rclpy.spin_once(self, timeout_sec= 0.1)
        if not self.arming_client.wait_for_service(timeout_sec= 5):
            self.get_logger().info('Error with connecting to arm server.')
            return 
        arm_req = CommandBool.Request()
        arm_req.val = True
        future = self.arming_client.call_async(arm_req)
            while not future.done():
            	await asyncio.sleep(0.1)
            result = future.result()
            return result.success
        self.get_logger().info('Arming request sent successfully.')
        if not self.setmode_client.wait_for_service(timeout_sec= 5):
            self.get_logger().info('Error with connecting to set mode server.')
            return 
        mode_req = SetMode.Request()
        mode_req.custom_mode = 'OFFBOARD'
        future_mode = self.setmode_client.call_async(future_mode)
            while not future_mode.done():
            	await asyncio.sleep(0.1)
            result = future_mode.result()
            return result.success
        self.get_logger().info('Set mode request sent successfully.')
        self.flight_started = True
def main(args = None):
    rclpy.init(args=args)
    client = LandClient()
    client.send_goal()
    time.sleep()
    client.destroy_node()
    rclpy.shutdown()
if __name__=='__main__':
    main()
