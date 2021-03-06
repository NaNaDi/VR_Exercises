#!/usr/bin/python

# import guacamole libraries
import avango
import avango.gua


### import application libraries
from lib.KeyboardInput import KeyboardInput
from lib.Hinge import Hinge
from lib.Arm import Arm
from lib.Hook import Hook


class Crane:

    # constructor
    def __init__(self,
        PARENT_NODE = None,
        TARGET_LIST = [],
        ):

        self.rotation = 0.0
        self.world_pos = (0,0,0)
        ### resources ###

        ## init base node for whole crane
        self.base_node = avango.gua.nodes.TransformNode(Name = "base_node")
        self.base_node.Transform.value = avango.gua.make_trans_mat(0.0,-0.1,0.0)
        PARENT_NODE.Children.value.append(self.base_node)

        self.targets = TARGET_LIST
        ## init internal sub-classes
        self.input = KeyboardInput()


        ## ToDo: init first hinge && connect rotation input 
        # ...
        #self.sf_rotation.connect_from(self.input.sf_rot_value1)
        self.firsthinge = Hinge()
        self.firsthinge.my_constructor(
            PARENT_NODE = self.base_node,
            DIAMETER = 0.05, # in meter
            HEIGHT = 0.01, # in meter
            ROT_OFFSET_MAT = avango.gua.make_identity_mat(), # the rotation offset relative to the parent coordinate system
            ROT_AXIS = avango.gua.Vec3(0,1,0), # the axis to rotate arround with the rotation input (default is head axis)
            ROT_CONSTRAINT = [-180.0, 180.0], # intervall with min and max rotation of this hinge
            BASE = True
            )
        self.firsthhinge_node = self.firsthinge.get_hinge_node()



        ## ToDo: init first arm-segment
        # ...
        self.firstarm = Arm(
            PARENT_NODE = self.firsthhinge_node,
            DIAMETER = 0.005, # in meter
            LENGTH = 0.075, # in meter
            ROT_OFFSET_MAT = avango.gua.make_identity_mat(), # the rotation offset relative to the parent coordinate system
            )
        self.firstarm_node = self.firstarm.get_arm_node()
        self.firstarm_node.Transform.value = avango.gua.make_trans_mat(0,0.04,0)



        ## ToDo: init second hinge && connect rotation input 
        # ...
        self.secondhinge = Hinge()
        self.secondhinge.my_constructor(
            PARENT_NODE = self.firstarm_node,
            DIAMETER = 0.02, # in meter
            HEIGHT = 0.02, # in meter
            ROT_OFFSET_MAT = avango.gua.make_identity_mat(), # the rotation offset relative to the parent coordinate system
            ROT_AXIS = avango.gua.Vec3(0,0,1), # the axis to rotate arround with the rotation input (default is head axis)
            ROT_CONSTRAINT = [-0.0, 90.0], # intervall with min and max rotation of this hinge
            )
        self.secondhinge_node = self.secondhinge.get_hinge_node()
        self.secondhinge_node.Transform.value = avango.gua.make_trans_mat(0,0.04,0)



        ## ToDo: init second arm-segment
        # ...
        self.secondarm = Arm(
            PARENT_NODE = self.secondhinge_node,
            DIAMETER = 0.005, # in meter
            LENGTH = 0.075, # in meter
            ROT_OFFSET_MAT = avango.gua.make_identity_mat(), # the rotation offset relative to the parent coordinate system
            )
        self.secondarm_node = self.secondarm.get_arm_node()
        self.secondarm_node.Transform.value = avango.gua.make_trans_mat(0,0.04,0)
        

        ## ToDo: init third hinge && connect rotation input 
        # ...
        self.thirdhinge = Hinge()
        self.thirdhinge.my_constructor(
            PARENT_NODE = self.secondarm_node,
            DIAMETER = 0.02, # in meter
            HEIGHT = 0.02, # in meter
            ROT_OFFSET_MAT = avango.gua.make_identity_mat(), # the rotation offset relative to the parent coordinate system
            ROT_AXIS = avango.gua.Vec3(0,0,1), # the axis to rotate arround with the rotation input (default is head axis)
            ROT_CONSTRAINT = [-90.0, 90.0], # intervall with min and max rotation of this hinge
            )
        self.thirdhinge_node = self.thirdhinge.get_hinge_node()
        self.thirdhinge_node.Transform.value = avango.gua.make_trans_mat(0,0.04,0)

        ## ToDo: init third arm-segment
        # ...
        self.thirdarm = Arm(
            PARENT_NODE = self.thirdhinge_node,
            DIAMETER = 0.005, # in meter
            LENGTH = 0.075, # in meter
            ROT_OFFSET_MAT = avango.gua.make_identity_mat(), # the rotation offset relative to the parent coordinate system
            )
        self.thirdarm_node = self.thirdarm.get_arm_node()
        self.thirdarm_node.Transform.value = avango.gua.make_trans_mat(0,0.04,0)


        ## ToDo: init hook
        self.firsthook = Hook()
        self.firsthook.my_constructor(
        PARENT_NODE = self.thirdarm_node,
        SIZE = 0.03,
        TARGET_LIST = self.targets,
        #TARGET_LIST = []
        )
        self.firsthook_node = self.firsthook.get_hook_node()
        self.firsthook_node.Transform.value = avango.gua.make_trans_mat(0,0.045,0)
        #self.firsthook.sf_mat.connect_from(self.thirdhinge.sf_world_pos)
 
