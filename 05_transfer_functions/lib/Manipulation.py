#!/usr/bin/python

#### import guacamole libraries
import avango
import avango.gua 
import avango.script
from avango.script import field_has_changed
import avango.daemon

### import application libraries
from lib.Device import MouseInput, SpacemouseInput, NewSpacemouseInput

### import python libraries
# ...
import time

import math


### global variables ###
#SPACEMOUSE_TYPE = "Spacemouse"
SPACEMOUSE_TYPE = "Blue Spacemouse" # blue LED

   
class ManipulationManager(avango.script.Script):

    ### input fields
    sf_key_1 = avango.SFBool()
    sf_key_2 = avango.SFBool()
    sf_key_3 = avango.SFBool()
    sf_key_4 = avango.SFBool()
    sf_key_5 = avango.SFBool()
    sf_key_6 = avango.SFBool()
    sf_key_7 = avango.SFBool()
    sf_key_8 = avango.SFBool()          

    sf_hand_mat = avango.gua.SFMatrix4()
    sf_dragging_trigger = avango.SFBool()


    # constructor
    def __init__(self):
        self.super(ManipulationManager).__init__()
    

    def my_constructor(self,
        PARENT_NODE = None,
        SCENE_ROOT = None,
        TARGET_LIST = [],
        ):
        

        ### external references ###        
        self.SCENE_ROOT = SCENE_ROOT
        self.TARGET_LIST = TARGET_LIST


        ### variables ###
        self.dragged_objects_list = []
        self.lf_hand_mat = avango.gua.make_identity_mat() # last frame hand matrix

        
        ## init hand geometry
        _loader = avango.gua.nodes.TriMeshLoader() # init trimesh loader to load external meshes
        
        self.hand_geometry = _loader.create_geometry_from_file("hand_geometry", "data/objects/hand.obj", avango.gua.LoaderFlags.DEFAULTS)
        self.hand_geometry.Transform.value = \
            avango.gua.make_rot_mat(45.0,1,0,0) * \
            avango.gua.make_rot_mat(180.0,0,1,0) * \
            avango.gua.make_scale_mat(0.06)
        self.hand_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0, 0.86, 0.54, 1.0))
        self.hand_geometry.Material.value.set_uniform("Emissivity", 0.9)
        self.hand_geometry.Material.value.set_uniform("Metalness", 0.1)  
        
        self.hand_transform = avango.gua.nodes.TransformNode(Name = "hand_transform")
        self.hand_transform.Children.value = [self.hand_geometry]
        PARENT_NODE.Children.value.append(self.hand_transform)
        self.hand_transform.Transform.connect_from(self.sf_hand_mat)
        

        ### init sub-classes ###
        
        ## init inputs
        self.mouseInput = MouseInput()
        self.mouseInput.my_constructor("gua-device-mouse")

        if SPACEMOUSE_TYPE == "Spacemouse":
            self.spacemouseInput = SpacemouseInput()
            self.spacemouseInput.my_constructor("gua-device-spacemouse")

        elif SPACEMOUSE_TYPE == "Blue Spacemouse":
            self.spacemouseInput = NewSpacemouseInput()
            self.spacemouseInput.my_constructor("gua-device-spacemouse")
        

        ## init manipulation techniques
        self.IPCManipulation = IsotonicPositionControlManipulation()
        self.IPCManipulation.my_constructor(self.mouseInput.mf_dof, self.mouseInput.mf_buttons)

        self.EPCManipulation = ElasticPositionControlManipulation()
        self.EPCManipulation.my_constructor(self.spacemouseInput.mf_dof, self.spacemouseInput.mf_buttons)

        self.IRCManipulation = IsotonicRateControlManipulation()
        self.IRCManipulation.my_constructor(self.mouseInput.mf_dof, self.mouseInput.mf_buttons)

        self.ERCManipulation = ElasticRateControlManipulation()
        self.ERCManipulation.my_constructor(self.spacemouseInput.mf_dof, self.spacemouseInput.mf_buttons)

        self.IACManipulation = IsotonicAccelerationControlManipulation()
        self.IACManipulation.my_constructor(self.mouseInput.mf_dof, self.mouseInput.mf_buttons)

        self.EACManipulation = ElasticAccelerationControlManipulation()
        self.EACManipulation.my_constructor(self.spacemouseInput.mf_dof, self.spacemouseInput.mf_buttons)
        
        self.NIIPCManipulation = NonIsomorphicIsotonicPositionControlManipulation()
        self.NIIPCManipulation.my_constructor(self.mouseInput.mf_dof, self.mouseInput.mf_buttons)

        self.NIERCManipulation = NonIsomorphicElasticRateControlManipulation()
        self.NIERCManipulation.my_constructor(self.spacemouseInput.mf_dof, self.spacemouseInput.mf_buttons)


        ## init keyboard sensor for system control
        self.keyboard_sensor = avango.daemon.nodes.DeviceSensor(DeviceService = avango.daemon.DeviceService())
        self.keyboard_sensor.Station.value = "gua-device-keyboard0"

        self.sf_key_1.connect_from(self.keyboard_sensor.Button16) # key 1
        self.sf_key_2.connect_from(self.keyboard_sensor.Button17) # key 2
        self.sf_key_3.connect_from(self.keyboard_sensor.Button18) # key 3
        self.sf_key_4.connect_from(self.keyboard_sensor.Button19) # key 4
        self.sf_key_5.connect_from(self.keyboard_sensor.Button20) # key 5
        self.sf_key_6.connect_from(self.keyboard_sensor.Button21) # key 6
        self.sf_key_7.connect_from(self.keyboard_sensor.Button22) # key 7
        self.sf_key_8.connect_from(self.keyboard_sensor.Button23) # key 8


        ### set initial states ###
        self.set_manipulation_technique(1) # switch to isotonic position control


    ### functions ###
    def set_manipulation_technique(self, INT):
        self.manipulation_technique = INT

        # disable prior manipulation technique
        self.IPCManipulation.enable_manipulation(False)
        self.EPCManipulation.enable_manipulation(False)
        self.IRCManipulation.enable_manipulation(False)
        self.ERCManipulation.enable_manipulation(False)
        self.IACManipulation.enable_manipulation(False)      
        self.EACManipulation.enable_manipulation(False)
        self.NIIPCManipulation.enable_manipulation(False)
        self.NIERCManipulation.enable_manipulation(False)
        
        # remove existing field connections    
        self.sf_hand_mat.disconnect()
        self.sf_dragging_trigger.disconnect()
        
        if self.manipulation_technique == 1: # isotonic position control     
            self.IPCManipulation.enable_manipulation(True)

            # init field connections      
            self.sf_hand_mat.connect_from(self.IPCManipulation.sf_mat)
            self.sf_dragging_trigger.connect_from(self.IPCManipulation.sf_action_trigger)
        
        elif self.manipulation_technique == 2: # elastic position control        
            self.EPCManipulation.enable_manipulation(True)

            # init field connections
            self.sf_hand_mat.connect_from(self.EPCManipulation.sf_mat)
            self.sf_dragging_trigger.connect_from(self.EPCManipulation.sf_action_trigger)            
        
        elif self.manipulation_technique == 3: # isotonic rate control        
            self.IRCManipulation.enable_manipulation(True)
        
            # init field connections
            self.sf_hand_mat.connect_from(self.IRCManipulation.sf_mat)
            self.sf_dragging_trigger.connect_from(self.IRCManipulation.sf_action_trigger)
        
        elif self.manipulation_technique == 4: # elastic rate control
            self.ERCManipulation.enable_manipulation(True)

            # init field connections      
            self.sf_hand_mat.connect_from(self.ERCManipulation.sf_mat)
            self.sf_dragging_trigger.connect_from(self.ERCManipulation.sf_action_trigger)
        
        elif self.manipulation_technique == 5: # isotonic acceleration control
            self.IACManipulation.enable_manipulation(True)

            # init field connections      
            self.sf_hand_mat.connect_from(self.IACManipulation.sf_mat)
            self.sf_dragging_trigger.connect_from(self.IACManipulation.sf_action_trigger)

        elif self.manipulation_technique == 6: # elastic acceleration control        
            self.EACManipulation.enable_manipulation(True)

            # init field connections      
            self.sf_hand_mat.connect_from(self.EACManipulation.sf_mat)
            self.sf_dragging_trigger.connect_from(self.EACManipulation.sf_action_trigger)

        elif self.manipulation_technique == 7:
            self.NIIPCManipulation.enable_manipulation(True)

            # init field connections      
            self.sf_hand_mat.connect_from(self.NIIPCManipulation.sf_mat)
            self.sf_dragging_trigger.connect_from(self.NIIPCManipulation.sf_action_trigger)

        elif self.manipulation_technique == 8:
            self.NIERCManipulation.enable_manipulation(True)

            # init field connections      
            self.sf_hand_mat.connect_from(self.NIERCManipulation.sf_mat)
            self.sf_dragging_trigger.connect_from(self.NIERCManipulation.sf_action_trigger)


    def start_dragging(self):  
        _hand_mat = self.hand_transform.WorldTransform.value

        for _node in self.TARGET_LIST:
            if self.is_highlight_material(_node.CurrentColor.value) == True: # a monkey node in close proximity
                _node.CurrentColor.value = avango.gua.Vec4(1.0, 0.0, 0.0, 1.0)
                _node.Material.value.set_uniform("Color", _node.CurrentColor.value) # switch to dragging material

                self.dragged_objects_list.append(_node) # add node for dragging
          
                ## dragging without snapping

                # clac tool-hand offset
                _dragging_offset_mat = avango.gua.make_inverse_mat(_hand_mat) * _node.Transform.value # object transformation in hand coordinate system
                _node.DraggingOffsetMatrix.value = _dragging_offset_mat # here you can store node dependent dragging transformations 

      
    def update_dragging_candidates(self):
        _hand_pos = self.hand_transform.WorldTransform.value.get_translate()
    
        for _node in self.TARGET_LIST:
            _pos = _node.Transform.value.get_translate() # a monkey position

            _dist = (_hand_pos - _pos).length() # hand-object distance
            _color = _node.CurrentColor.value

            ## toggle object highlight
            if _dist < 0.025 and self.is_default_material(_color) == True:
                _node.CurrentColor.value = avango.gua.Vec4(0.0, 1.0, 0.0, 1.0)
                _node.Material.value.set_uniform("Color", _node.CurrentColor.value) # switch to highlight material

            elif _dist > 0.03 and self.is_highlight_material(_color) == True:
                _node.CurrentColor.value = avango.gua.Vec4(1.0, 1.0, 1.0, 1.0)
                _node.Material.value.set_uniform("Color", _node.CurrentColor.value) # switch to default material
    

    def object_dragging(self):
        # apply hand movement to (all) dragged objects
        for _node in self.dragged_objects_list:
            _node.Transform.value = self.hand_transform.WorldTransform.value * _node.DraggingOffsetMatrix.value # apply tool-hand offset to absolute hand transformation            

  
    def stop_dragging(self):  
        ## handle all dragged objects
        for _node in self.dragged_objects_list:      
            _node.CurrentColor.value = avango.gua.Vec4(0.0, 1.0, 0.0, 1.0)
            _node.Material.value.set_uniform("Color", _node.CurrentColor.value) # switch to highlight material
    
        self.dragged_objects_list = [] # clear list


    def is_default_material(self, VEC4):
        return VEC4.x == 1.0 and VEC4.y == 1.0 and VEC4.z == 1.0 and VEC4.w == 1.0


    def is_highlight_material(self, VEC4):
        return VEC4.x == 0.0 and VEC4.y == 1.0 and VEC4.z == 0.0 and VEC4.w == 1.0


    def is_dragging_material(self, VEC4):
        return VEC4.x == 1.0 and VEC4.y == 0.0 and VEC4.z == 0.0 and VEC4.w == 1.0
      
    
    ### callback functions ###

    @field_has_changed(sf_key_1)
    def sf_key_1_changed(self):
        if self.sf_key_1.value == True: # key is pressed
            self.set_manipulation_technique(1) # switch to isotonic position control
           

    @field_has_changed(sf_key_2)
    def sf_key_2_changed(self):
        if self.sf_key_2.value == True: # key is pressed
            self.set_manipulation_technique(2) # switch to elastic position control


    @field_has_changed(sf_key_3)
    def sf_key_3_changed(self):
        if self.sf_key_3.value == True: # key is pressed
            self.set_manipulation_technique(3) # switch to isotonic rate control


    @field_has_changed(sf_key_4)
    def sf_key_4_changed(self):
        if self.sf_key_4.value == True: # key is pressed
            self.set_manipulation_technique(4) # switch to elastic rate control
      

    @field_has_changed(sf_key_5)
    def sf_key_5_changed(self):
        if self.sf_key_5.value == True: # key is pressed
            self.set_manipulation_technique(5) # switch to isotonic acceleration control


    @field_has_changed(sf_key_6)
    def sf_key_6_changed(self):
        if self.sf_key_6.value == True: # key is pressed
            self.set_manipulation_technique(6) # switch to elastic acceleration control

    @field_has_changed(sf_key_7)
    def sf_key_7_changed(self):
        print("field_has_changed")
        if self.sf_key_7.value == True: # key is pressed
            self.set_manipulation_technique(7) # switch to elastic acceleration control

    @field_has_changed(sf_key_8)
    def sf_key_8_changed(self):
        if self.sf_key_8.value == True: # key is pressed
            self.set_manipulation_technique(8) # switch to elastic acceleration control


    @field_has_changed(sf_dragging_trigger)
    def sf_dragging_trigger_changed(self):
        if self.sf_dragging_trigger.value == True:
            self.start_dragging()  
        else:
            self.stop_dragging()
     

    def evaluate(self): # evaluated every frame if any input field has changed (incl. dependency evaluation)
        self.update_dragging_candidates()

        self.object_dragging() # possibly drag object with hand input


        ## print covered distance and hand velocity as debug output
        _distance = (self.sf_hand_mat.value.get_translate() - self.lf_hand_mat.get_translate()).length()
        _velocity = _distance * 60.0 # application loop runs with 60Hz
        self.lf_hand_mat = self.sf_hand_mat.value
        
        #print(round(_distance, 3), "m/frame  ", round(_velocity, 2), "m/s")



class Manipulation(avango.script.Script):

    ### input fields
    mf_dof = avango.MFFloat()
    mf_dof.value = [0.0,0.0,0.0,0.0,0.0,0.0,0.0] # init 7 channels

    mf_buttons = avango.MFBool()
    mf_buttons.value = [False,False] # init 2 channels


    ### output_fields
    sf_mat = avango.gua.SFMatrix4()
    sf_mat.value = avango.gua.make_identity_mat()

    sf_action_trigger = avango.SFBool()
    

    ### constructor
    def __init__(self):
        self.super(Manipulation).__init__()

        ### variables ###
        self.type = ""
        self.enable_flag = False

    
    ### callback functions ###
    def evaluate(self): # evaluated every frame if any input field has changed  
        if self.enable_flag == True:
            self.manipulate()


    @field_has_changed(mf_buttons)
    def mf_buttons_changed(self):
        if self.enable_flag == True:
            _left_button = self.mf_buttons.value[0]
            _right_button = self.mf_buttons.value[1]

            self.sf_action_trigger.value = _left_button ^ _right_button # button left XOR button right

        
    ### functions ###
    def enable_manipulation(self, FLAG):   
        self.enable_flag = FLAG
    
        if self.enable_flag == True:
            print(self.type + " enabled")
    
            self.reset()
      
   
    def manipulate(self):
        raise NotImplementedError("To be implemented by a subclass.")


    def reset(self):
        raise NotImplementedError("To be implemented by a subclass.")
    
    
    def clamp_matrix(self, MATRIX):    
        # clamp translation to certain range (within screen space)
        _x_range = 0.3 # in meter
        _y_range = 0.15 # in meter
        _z_range = 0.15 # in meter    

        MATRIX.set_element(0,3, min(_x_range, max(-_x_range, MATRIX.get_element(0,3)))) # clamp x-axis
        MATRIX.set_element(1,3, min(_y_range, max(-_y_range, MATRIX.get_element(1,3)))) # clamp y-axis
        MATRIX.set_element(2,3, min(_z_range, max(-_z_range, MATRIX.get_element(2,3)))) # clamp z-axis
         
        return MATRIX



### ISOTONIC DEVICE MAPPINGS ##
#1
class IsotonicPositionControlManipulation(Manipulation):

    def my_constructor(self, MF_DOF, MF_BUTTONS):
        self.type = "isotonic-position-control"
    
        # init field connections
        self.mf_dof.connect_from(MF_DOF)
        self.mf_buttons.connect_from(MF_BUTTONS)


    ## implement respective base-class function
    def manipulate(self):
        _x = self.mf_dof.value[0]
        _y = self.mf_dof.value[1]
        _z = self.mf_dof.value[2]
          
        _x *= 0.1
        _y *= 0.1
        _z *= 0.1
       
        # accumulate input
        _new_mat = avango.gua.make_trans_mat(_x, _y, _z) * self.sf_mat.value

        # possibly clamp matrix (to screen space borders)
        _new_mat = self.clamp_matrix(_new_mat)

        self.sf_mat.value = _new_mat # apply new matrix to field
    

    ## implement respective base-class function    
    def reset(self):
        self.sf_mat.value = avango.gua.make_identity_mat() # snap hand back to screen center

#2
class IsotonicRateControlManipulation(Manipulation):

    def my_constructor(self, MF_DOF, MF_BUTTONS):
        self.type = "isotonic-rate-control"

        self._x_val = 0
        self._y_val = 0
        self._z_val = 0
        self._x_pos = 0
        self._y_pos = 0
        self._z_pos = 0
          
        # init field connections
        self.mf_dof.connect_from(MF_DOF)
        self.mf_buttons.connect_from(MF_BUTTONS)


    ## implement respective base-class function
    def manipulate(self):
        self._x = self.mf_dof.value[0]
        self._y = self.mf_dof.value[1]
        self._z = self.mf_dof.value[2]

        self._x *= 0.1
        self._y *= 0.1
        self._z *= 0.1


        self._x_val = self._x + self._x_val

        self._y_val = self._y + self._y_val

        self._z_val = self._z + self._z_val

        self._x_pos += self._x_val

        self._y_pos += self._y_val

        self._z_pos += self._z_val
        
        velocity_factor = 100



         #accumulate imput
        _new_mat = avango.gua.make_trans_mat(self._x_pos/velocity_factor, self._y_pos/velocity_factor, self._z_pos/velocity_factor)

        # possibly clamp matrix (to screen space borders)
        _new_mat = self.clamp_matrix(_new_mat)

        self.sf_mat.value = _new_mat # apply new matrix to field



    
    
    ## implement respective base-class function
    def reset(self):
        self.sf_mat.value = avango.gua.make_identity_mat() # snap hand back to screen center

#5
class IsotonicAccelerationControlManipulation(Manipulation):

    def my_constructor(self, MF_DOF, MF_BUTTONS):
        self.type = "isotonic-acceleration-control"

        self._x_val = 0
        self._y_val = 0
        self._z_val = 0
        self._x_pos = 0
        self._y_pos = 0
        self._z_pos = 0
        self._x_acc = 0
        self._y_acc = 0
        self._z_acc = 0
          
        # init field connections
        self.mf_dof.connect_from(MF_DOF)
        self.mf_buttons.connect_from(MF_BUTTONS)


    ## implement respective base-class function
    def manipulate(self):
        self._x = self.mf_dof.value[0]
        self._y = self.mf_dof.value[1]
        self._z = self.mf_dof.value[2]

        self._x *= 0.1
        self._y *= 0.1
        self._z *= 0.1


        self._x_acc = self._x + self._x_acc

        self._y_acc = self._y + self._y_acc

        self._z_acc = self._z + self._z_acc

        self._x_val += self._x_acc

        self._y_val += self._y_acc

        self._z_val += self._z_acc

        self._x_pos += self._x_val

        self._y_pos += self._y_val

        self._z_pos += self._z_val
        
        velocity_factor = 100



         #accumulate imput
        _new_mat = avango.gua.make_trans_mat(self._x_pos/velocity_factor, self._y_pos/velocity_factor, self._z_pos/velocity_factor)

        # possibly clamp matrix (to screen space borders)
        _new_mat = self.clamp_matrix(_new_mat)

        self.sf_mat.value = _new_mat # apply new matrix to field



    
    
    ## implement respective base-class function
    def reset(self):
        self.sf_mat.value = avango.gua.make_identity_mat() # snap hand back to screen center
     
    

### ELASTIC DEVICE MAPPINGS ###
#4
class ElasticPositionControlManipulation(Manipulation):

    def my_constructor(self, MF_DOF, MF_BUTTONS):
        self.type = "elastic-position-control"
      
        # init field connections
        self.mf_dof.connect_from(MF_DOF)
        self.mf_buttons.connect_from(MF_BUTTONS)


    ## implement respective base-class function
    def manipulate(self):
        _x = self.mf_dof.value[0]
        _y = self.mf_dof.value[1]
        _z = self.mf_dof.value[2]
        _rx = self.mf_dof.value[3]
        _ry = self.mf_dof.value[4]
        _rz = self.mf_dof.value[5]

        _x *= 0.1
        _y *= 0.1
        _z *= 0.1
        _rx *= 0.1
        _ry *= 0.1
        _rz *= 0.1

        #accumulate imput
        _new_mat = avango.gua.make_trans_mat(_x,_y,_z)*avango.gua.make_rot_mat(_rx,1,0,0)*avango.gua.make_rot_mat(_ry,0,1,0)*avango.gua.make_rot_mat(_rz, 0,0,1)

        # possibly clamp matrix (to screen space borders)
        _new_mat = self.clamp_matrix(_new_mat)

        self.sf_mat.value = _new_mat # apply new matrix to field

         
    ## implement respective base-class function
    def reset(self):
         self.sf_mat.value = avango.gua.make_identity_mat() # snap hand back to screen center

#4
class ElasticRateControlManipulation(Manipulation):

    def my_constructor(self, MF_DOF, MF_BUTTONS):
        self.type = "elastic-rate-control"
        # init field connections
        self.mf_dof.connect_from(MF_DOF)
        self.mf_buttons.connect_from(MF_BUTTONS)
        
       # timer = avango.nodes.TimeSensor()
        #self.TimeIn.connect_from(timer.time)

        self._x_val = 0
        self._y_val = 0
        self._z_val = 0
        self._rx_val = 0
        self._ry_val = 0
        self._rz_val = 0



    ## implement respective base-class function
    def manipulate(self):
        self._x = self.mf_dof.value[0]
        self._y = self.mf_dof.value[1]
        self._z = self.mf_dof.value[2]
        self._rx = self.mf_dof.value[3]
        self._ry = self.mf_dof.value[4]
        self._rz = self.mf_dof.value[5]

        self._x *= 0.1
        self._y *= 0.1
        self._z *= 0.1
        self._rx *= 0.1
        self._ry *= 0.1
        self._rz *= 0.1

        #timer = avango.nodes.TimeSensor()
        #self.TimeIn.connect_from(timer.Time)

        if(self._x != 0):
            self._x_val = self._x + self._x_val

        if(self._y != 0):
            self._y_val = self._y + self._y_val

        if(self._z != 0):
            self._z_val = self._z + self._z_val

        if(self._rx != 0):
            self._rx_val = self._rx + self._rx_val

        if(self._ry != 0):
            self._ry_val = self._ry + self._ry_val

        if(self._rz != 0):
            self._rz_val = self._rz + self._rz_val



         #accumulate imput
        _new_mat = avango.gua.make_trans_mat(self._x_val,self._y_val,self._z_val)*avango.gua.make_rot_mat(self._rx_val,1,0,0)*avango.gua.make_rot_mat(self._ry_val,0,1,0)*avango.gua.make_rot_mat(self._rz_val, 0,0,1)

        # possibly clamp matrix (to screen space borders)
        _new_mat = self.clamp_matrix(_new_mat)

        self.sf_mat.value = _new_mat # apply new matrix to field

    def reset(self):
        self.sf_mat.value = avango.gua.make_identity_mat() # snap hand back to screen center

#6
class ElasticAccelerationControlManipulation(Manipulation):

    TimeIn = avango.SFFloat()

    def my_constructor(self, MF_DOF, MF_BUTTONS):
        self.type = "elastic-acceleration-control"
      
        self._x_val = 0
        self._y_val = 0
        self._z_val = 0
        self._rx_val = 0
        self._ry_val = 0
        self._rz_val = 0
        self._x_pos = 0
        self._y_pos = 0
        self._z_pos = 0
        self._rx_pos = 0
        self._ry_pos = 0
        self._rz_pos = 0
        self._x_acc = 0
        self._y_acc = 0
        self._z_acc = 0
        self._rx_acc = 0
        self._ry_acc = 0
        self._rz_acc = 0
          
        # init field connections
        self.mf_dof.connect_from(MF_DOF)
        self.mf_buttons.connect_from(MF_BUTTONS)


    ## implement respective base-class function
    def manipulate(self):
        self._x = self.mf_dof.value[0]
        self._y = self.mf_dof.value[1]
        self._z = self.mf_dof.value[2]
        self._rx = self.mf_dof.value[3]
        self._ry = self.mf_dof.value[4]
        self._rz = self.mf_dof.value[5]

        self._x *= 0.1
        self._y *= 0.1
        self._z *= 0.1
        self._rx *= 0.1
        self._ry *= 0.1
        self._rz *= 0.1


        self._x_acc = self._x + self._x_acc

        self._y_acc = self._y + self._y_acc

        self._z_acc = self._z + self._z_acc

        self._rx_acc = self._rx + self._rx_acc

        self._ry_acc = self._ry + self._ry_acc

        self._rz_acc = self._rz + self._rz_acc

        self._x_val += self._x_acc

        self._y_val += self._y_acc

        self._z_val += self._z_acc

        self._rx_val += self._rx_acc

        self._ry_val += self._ry_acc

        self._rz_val += self._rz_acc

        self._x_pos += self._x_val

        self._y_pos += self._y_val

        self._z_pos += self._z_val

        self._rx_pos += self._rx_val

        self._ry_pos += self._ry_val

        self._rz_pos += self._rz_val
        
        velocity_factor = 100



         #accumulate imput
        _new_mat = avango.gua.make_trans_mat(self._x_pos/velocity_factor, self._y_pos/velocity_factor, self._z_pos/velocity_factor)*avango.gua.make_rot_mat(self._rx_pos/velocity_factor,1,0,0)*avango.gua.make_rot_mat(self._ry_pos/velocity_factor,0,1,0)*avango.gua.make_rot_mat(self._rz_pos/velocity_factor, 0,0,1)

        # possibly clamp matrix (to screen space borders)
        _new_mat = self.clamp_matrix(_new_mat)

        self.sf_mat.value = _new_mat # apply new matrix to field



    
    
    ## implement respective base-class function
    def reset(self):
        self.sf_mat.value = avango.gua.make_identity_mat() # snap hand back to screen center

class NonIsomorphicIsotonicPositionControlManipulation(Manipulation):

    def my_constructor(self, MF_DOF, MF_BUTTONS):
        self.type = "non-isometric-isotonic-position-control"
    
        # init field connections
        self.mf_dof.connect_from(MF_DOF)
        self.mf_buttons.connect_from(MF_BUTTONS)


    ## implement respective base-class function
    def manipulate(self):
        _x = self.mf_dof.value[0]
        _y = self.mf_dof.value[1]
        _z = self.mf_dof.value[2]

        _mag = math.hypot(_x,_y)

        if _x != 0 and _y != 0:
            #Kosinussatz
            alpha = math.acos((_x * _x - _y * _y - _mag * _mag)/(-2 * _y * _mag))
            beta = math.acos((_y * _y - _mag * _mag - _x * _x)/(-2 * _mag * _x))

            _mag = math.pow(_mag, 3)

            #print(_mag)

            #Sinussatz
            if _x > 0:
                _x = _mag * math.sin(alpha) / math.sin(90)
            else:
                _x = (_mag * math.sin(alpha) / math.sin(90))*-1

            if _y > 0:
                _y = _mag * math.sin(beta) / math.sin(90)
            else:
                _y = (_mag * math.sin(beta) / math.sin(90))*-1

        _x *= 0.1
        _y *= 0.1
        _z *= 0.1

        #print('_x : ', _x)
        #print('_y : ', _y)
       
        # accumulate input
        _new_mat = avango.gua.make_trans_mat(_x, _y, _z) * self.sf_mat.value

        # possibly clamp matrix (to screen space borders)
        _new_mat = self.clamp_matrix(_new_mat)

        self.sf_mat.value = _new_mat # apply new matrix to field

        #print('trans-vec: ', self.sf_mat.value.get_translate())
    

    ## implement respective base-class function    
    def reset(self):
        self.sf_mat.value = avango.gua.make_identity_mat() # snap hand back to screen center

class NonIsomorphicElasticRateControlManipulation(Manipulation):

    def my_constructor(self, MF_DOF, MF_BUTTONS):
        self.type = "non-isomorphic-elastic-rate-control"
        # init field connections
        self.mf_dof.connect_from(MF_DOF)
        self.mf_buttons.connect_from(MF_BUTTONS)
        
       # timer = avango.nodes.TimeSensor()
        #self.TimeIn.connect_from(timer.time)

        self._x_val = 0
        self._y_val = 0
        self._z_val = 0




    ## implement respective base-class function
    def manipulate(self):
        _x = self.mf_dof.value[0]
        _y = self.mf_dof.value[1]
        _z = self.mf_dof.value[2]




        _x *= 0.1
        _y *= 0.1
        _z *= 0.1



    #für X-Y-Achse
        if _x != 0 and _y != 0:
            _mag = math.hypot(_x,_y)

            _mag = math.pow(_mag, 3)
            _x = _x*math.pow(_mag,2)
            _y = _y*math.pow(_mag,2)

        
    
        #für X-Z-Achse
        if _x != 0 and _z != 0:
            _mag = math.hypot(_x,_z)

            _mag = math.pow(_mag, 3)
            _x = _x*math.pow(_mag,2)
            _z = _z*math.pow(_mag,2)


        #für Y-Z-Achse
        if _z != 0 and _y != 0:
            _mag = math.hypot(_z,_y)

            _mag = math.pow(_mag, 3)
            _z = _z*math.pow(_mag,2)
            _y = _y*math.pow(_mag,2)


        if(_x != 0):
            self._x_val = _x + self._x_val

        if(_y != 0):
            self._y_val = _y + self._y_val

        if(_z != 0):
            self._z_val = _z + self._z_val


         #accumulate imput
        _new_mat = avango.gua.make_trans_mat(self._x_val,self._y_val,self._z_val)

        # possibly clamp matrix (to screen space borders)
        _new_mat = self.clamp_matrix(_new_mat)

        self.sf_mat.value = _new_mat # apply new matrix to field

    def reset(self):
        self.sf_mat.value = avango.gua.make_identity_mat() # snap hand back to screen center

        
