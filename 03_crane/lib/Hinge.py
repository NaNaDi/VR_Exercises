#!/usr/bin/python

# import guacamole libraries
import avango
import avango.gua
import avango.script
from avango.script import field_has_changed
from lib.KeyboardInput import KeyboardInput


class Hinge(avango.script.Script):

    ## input fields
    sf_rot_value = avango.SFFloat()
    
    ## output field
    sf_world_pos = avango.avango.gua.SFMatrix4()

    ### class variables ###

    # Number of Hinge instances that have already been created.
    number_of_instances = 0
   
    # constructor
    def __init__(self):
        self.super(Hinge).__init__()

        ## get unique id for this instance
        self.id = Hinge.number_of_instances
        Hinge.number_of_instances += 1

        self.input = KeyboardInput()

        self.degree = 0.0




    def my_constructor(self,
        PARENT_NODE = None,
        DIAMETER = 0.1, # in meter
        HEIGHT = 0.1, # in meter
        ROT_OFFSET_MAT = avango.gua.make_identity_mat(), # the rotation offset relative to the parent coordinate system
        ROT_AXIS = avango.gua.Vec3(0,1,0), # the axis to rotate arround with the rotation input (default is head axis)
        ROT_CONSTRAINT = [-45.0, 45.0], # intervall with min and max rotation of this hinge
        BASE = False,
        ):


        ### variables ###
        ## ToDo: evtl. init further variables


        ### parameters ###        
        self.rot_axis = ROT_AXIS
        
        self.rot_constraint = ROT_CONSTRAINT

        self.base = BASE

        self.parent = PARENT_NODE


        ### resources ###

        _loader = avango.gua.nodes.TriMeshLoader() # get trimesh loader to load external tri-meshes

        ## ToDo: init hinge node(s)
        self.hinge_geometry = _loader.create_geometry_from_file("hinge_geometry", "data/objects/sphere.obj", avango.gua.LoaderFlags.DEFAULTS)
        self.hinge_geometry.Transform.value = avango.gua.make_trans_mat(0.0,0.0,0.0) * avango.gua.make_scale_mat(DIAMETER,HEIGHT,DIAMETER)
        self.hinge_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0,0.0,0.0,1.0))

        self.hinge_node = avango.gua.nodes.TransformNode(Name = "HingeNode")
        self.hinge_node.Children.value.append(self.hinge_geometry)

        PARENT_NODE.Children.value.append(self.hinge_node)

        '''
        if self.base:
            self.sf_rot_value.connect_from(self.input.sf_rot_value0)
        else:
            self.sf_rot_value.connect_from(self.input.sf_rot_value1)
        '''

        if self.id == 0:
            self.sf_rot_value.connect_from(self.input.sf_rot_value0)
        elif self.id == 1:
            self.sf_rot_value.connect_from(self.input.sf_rot_value1)
        elif self.id == 2:
            self.sf_rot_value.connect_from(self.input.sf_rot_value2)

        
    ### callback functions ###
    def get_hinge_node(self):
        return self.hinge_node

    def get_world_pos(self,trans_val):
        _pos = self.parent.Transform.value * trans_val
        return _pos
        #print("parent: ",self.parent)

    
    @field_has_changed(sf_rot_value)
    def sf_rot_value_changed(self):
        pass
        ## ToDo: accumulate input to hinge node && consider rotation contraints of this hinge
        # ...
        self.degree += self.sf_rot_value.value
        #testpos = self.parent.Transform.value.get_translate() * self.hinge_node.Transform.value.get_translate()
        #print("Hinge ",self.id, testpos)
        #print(self.degree)
        #print("HingeTrans: ", self.sf_rot_value.value)
        if self.degree > self.rot_constraint[0] and self.degree < self.rot_constraint[1]:
            self.hinge_node.Transform.value = self.hinge_node.Transform.value * avango.gua.make_rot_mat(self.sf_rot_value.value, self.rot_axis)
            #print("Hinge trans: ", self.hinge_node.Transform.value)
        self.sf_world_pos.value =  self.get_world_pos(self.hinge_node.Transform.value)
        #print("world_pos.value: ", self.sf_world_pos.value)
        #print("test", test)
        #self.get_world_pos(self.hinge_node.Transform.value)