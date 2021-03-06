#!/usr/bin/python

### import guacamole libraries ###
import avango
import avango.gua
import avango.script
from avango.script import field_has_changed
import avango.daemon

import math





class ManipulationManager(avango.script.Script):

    ## input fields
    sf_key_1 = avango.SFBool()
    sf_key_2 = avango.SFBool()
    sf_key_3 = avango.SFBool()
    sf_key_4 = avango.SFBool()

    ## constructor
    def __init__(self):
        self.super(ManipulationManager).__init__()    
    
    
    def my_constructor(self,
        SCENEGRAPH = None,
        NAVIGATION_NODE = None,
        POINTER_TRACKING_STATION = "",
        TRACKING_TRANSMITTER_OFFSET = avango.gua.make_identity_mat(),
        POINTER_DEVICE_STATION = "",
        HEAD_NODE = None,
        ):
        

        ### variables ###
        self.active_manipulation_technique = None

        ### resources ###
        self.keyboard_sensor = avango.daemon.nodes.DeviceSensor(DeviceService = avango.daemon.DeviceService())
        self.keyboard_sensor.Station.value = "gua-device-keyboard0"

        self.sf_key_1.connect_from(self.keyboard_sensor.Button16) # key 1
        self.sf_key_2.connect_from(self.keyboard_sensor.Button17) # key 2
        self.sf_key_3.connect_from(self.keyboard_sensor.Button18) # key 3
        self.sf_key_4.connect_from(self.keyboard_sensor.Button19) # key 4

    
        ## init manipulation techniques
        self.virtualRay = VirtualRay()
        self.virtualRay.my_constructor(SCENEGRAPH, NAVIGATION_NODE, POINTER_TRACKING_STATION, TRACKING_TRANSMITTER_OFFSET, POINTER_DEVICE_STATION)

        self.virtualHand = VirtualHand()
        self.virtualHand.my_constructor(SCENEGRAPH, NAVIGATION_NODE, POINTER_TRACKING_STATION, TRACKING_TRANSMITTER_OFFSET, POINTER_DEVICE_STATION)

        self.goGo = GoGo()
        self.goGo.my_constructor(SCENEGRAPH, NAVIGATION_NODE, POINTER_TRACKING_STATION, TRACKING_TRANSMITTER_OFFSET, POINTER_DEVICE_STATION, HEAD_NODE)

        self.homer = Homer()
        self.homer.my_constructor(SCENEGRAPH, NAVIGATION_NODE, POINTER_TRACKING_STATION, TRACKING_TRANSMITTER_OFFSET, POINTER_DEVICE_STATION, HEAD_NODE)
        
    
        ### set initial states ###
        self.set_manipulation_technique(0) # switch to virtual-ray manipulation technique



    ### functions ###
    def set_manipulation_technique(self, INT):
        # possibly disable prior technique
        if self.active_manipulation_technique is not None:
            self.active_manipulation_technique.enable(False)
    
        # enable new technique
        if INT == 0: # virtual-ray
            print("switch to Virtual-Ray technique")
            self.active_manipulation_technique = self.virtualRay

        elif INT == 1: # virtual-hand
            print("switch to Virtual-Hand technique")
            self.active_manipulation_technique = self.virtualHand

        elif INT == 2: # go-go
            print("switch to Go-Go technique")
            self.active_manipulation_technique = self.goGo

        elif INT == 3: # HOMER
            print("switch to HOMER technique")
            self.active_manipulation_technique = self.homer
            
        self.active_manipulation_technique.enable(True)


    ### callback functions ###
    @field_has_changed(sf_key_1)
    def sf_key_1_changed(self):
        if self.sf_key_1.value == True: # key is pressed
            self.set_manipulation_technique(0) # switch to Virtual-Ray manipulation technique
            

    @field_has_changed(sf_key_2)
    def sf_key_2_changed(self):
        if self.sf_key_2.value == True: # key is pressed
            self.set_manipulation_technique(1) # switch to Virtual-Hand manipulation technique


    @field_has_changed(sf_key_3)
    def sf_key_3_changed(self):
        if self.sf_key_3.value == True: # key is pressed
            self.set_manipulation_technique(2) # switch to Go-Go manipulation technique


    @field_has_changed(sf_key_4)
    def sf_key_4_changed(self):
        if self.sf_key_4.value == True: # key is pressed
            self.set_manipulation_technique(3) # switch to HOMER manipulation technique



class ManipulationTechnique(avango.script.Script):

    ## input fields
    sf_button = avango.SFBool()

    ## constructor
    def __init__(self):
        self.super(ManipulationTechnique).__init__()
               

    def my_constructor(self,
        SCENEGRAPH = None,
        NAVIGATION_NODE = None,
        POINTER_TRACKING_STATION = None,
        TRACKING_TRANSMITTER_OFFSET = avango.gua.make_identity_mat(),
        POINTER_DEVICE_STATION = None,
        ):


        ### external references ###
        self.SCENEGRAPH = SCENEGRAPH
            
        ### variables ###
        self.enable_flag = False
        
        ## dragging
        self.dragged_node = None
        self.dragging_offset_mat = avango.gua.make_identity_mat()
                
        ## picking
        self.pick_result = None
        
        self.white_list = []   
        self.black_list = ["invisible"]

        self.pick_options = avango.gua.PickingOptions.PICK_ONLY_FIRST_OBJECT \
                            | avango.gua.PickingOptions.GET_POSITIONS \
                            | avango.gua.PickingOptions.GET_NORMALS \
                            | avango.gua.PickingOptions.GET_WORLD_POSITIONS \
                            | avango.gua.PickingOptions.GET_WORLD_NORMALS


        ### resources ###
        self.mode = True
    
        ## init sensors
        self.pointer_tracking_sensor = avango.daemon.nodes.DeviceSensor(DeviceService = avango.daemon.DeviceService())
        self.pointer_tracking_sensor.Station.value = POINTER_TRACKING_STATION
        self.pointer_tracking_sensor.TransmitterOffset.value = TRACKING_TRANSMITTER_OFFSET
            
        self.pointer_device_sensor = avango.daemon.nodes.DeviceSensor(DeviceService = avango.daemon.DeviceService())
        self.pointer_device_sensor.Station.value = POINTER_DEVICE_STATION

        ## init field connections
        self.sf_button.connect_from(self.pointer_device_sensor.Button0)


        ## init nodes
        self.pointer_node = avango.gua.nodes.TransformNode(Name = "pointer_node")
        self.pointer_node.Transform.connect_from(self.pointer_tracking_sensor.Matrix)
        self.pointer_node.Tags.value = ["invisible"]
        NAVIGATION_NODE.Children.value.append(self.pointer_node)
        

        self.ray = avango.gua.nodes.Ray() # required for trimesh intersection
            
        self.always_evaluate(True) # change global evaluation policy



    ### functions ###
    def enable(self, BOOL):
        self.enable_flag = BOOL
        
        if self.enable_flag == True:
            self.pointer_node.Tags.value = [] # set tool visible
        else:
            self.stop_dragging() # possibly stop active dragging process
            
            self.pointer_node.Tags.value = ["invisible"] # set tool invisible


    def calc_pick_result(self, PICK_MAT = avango.gua.make_identity_mat(), PICK_LENGTH = 1.0):
        ## update ray parameters
        self.ray.Origin.value = PICK_MAT.get_translate()

        _vec = avango.gua.make_rot_mat(PICK_MAT.get_rotate_scale_corrected()) * avango.gua.Vec3(0.0,0.0,-1.0)
        _vec = avango.gua.Vec3(_vec.x,_vec.y,_vec.z)

        self.ray.Direction.value = _vec * PICK_LENGTH

        ## intersect
        _mf_pick_result = self.SCENEGRAPH.ray_test(self.ray, self.pick_options, self.white_list, self.black_list)

        return _mf_pick_result    

    
    def start_dragging(self, NODE):
        self.dragged_node = NODE        
        self.dragging_offset_mat = avango.gua.make_inverse_mat(self.pointer_node.WorldTransform.value) * self.dragged_node.WorldTransform.value # object transformation in pointer coordinate system
  
    def stop_dragging(self): 
        self.dragged_node = None
        self.dragging_offset_mat = avango.gua.make_identity_mat()
        self.mode = True


    def dragging(self, _trans_node, offset = 0.0):
        #print("before ", self.dragging_offset_mat)
        #if self.mode == True:
        #    self.dragging_offset_mat = avango.gua.make_trans_mat(0,0,offset) * self.dragging_offset_mat
        #    self.mode = False
        #print("after ", self.dragging_offset_mat)
        if self.dragged_node is not None: # object to drag
            #self.dragging_offset_mat = avango.gua.make_inverse_mat(self.pointer_node.WorldTransform.value) * self.dragged_node.WorldTransform.value
            _new_mat = _trans_node.WorldTransform.value * self.dragging_offset_mat # new object position in world coodinates
            _new_mat = avango.gua.make_inverse_mat(self.dragged_node.Parent.value.WorldTransform.value) * _new_mat # transform new object matrix from global to local space
            #print("before: ", _new_mat)
            #_new_mat = avango.gua.make_trans_mat(0,0,offset) * _new_mat
            #print("after: ", _new_mat)
            self.dragged_node.Transform.value = _new_mat


    ### callback functions ###

    @field_has_changed(sf_button)
    def sf_button_changed(self):
        if self.sf_button.value == True: # button pressed
            if self.pick_result is not None: # something was hit
                _node = self.pick_result.Object.value # get intersected geometry node
                _node = _node.Parent.value # take the parent node of the geomtry node (the whole object)

                self.start_dragging(_node)

        else: # button released
            self.stop_dragging()
            
            
    def evaluate(self): # evaluated every frame
        raise NotImplementedError("To be implemented by a subclass.")
            
            

class VirtualRay(ManipulationTechnique):

    ## constructor
    def __init__(self):
        self.super(VirtualRay).__init__()


    def my_constructor(self,
        SCENEGRAPH = None,
        NAVIGATION_NODE = None,
        POINTER_TRACKING_STATION = None,
        TRACKING_TRANSMITTER_OFFSET = avango.gua.make_identity_mat(),
        POINTER_DEVICE_STATION = None,
        ):

        ManipulationTechnique.my_constructor(self, SCENEGRAPH, NAVIGATION_NODE, POINTER_TRACKING_STATION, TRACKING_TRANSMITTER_OFFSET, POINTER_DEVICE_STATION) # call base class constructor


        ### additional parameters ###

        ## visualization
        self.ray_length = 2.0 # in meter
        self.ray_thickness = 0.0075 # in meter

        self.intersection_point_size = 0.01 # in meter


        ### additional resources ###
        _loader = avango.gua.nodes.TriMeshLoader()

        self.ray_geometry = _loader.create_geometry_from_file("ray_geometry", "data/objects/cylinder.obj", avango.gua.LoaderFlags.DEFAULTS)
        self.ray_geometry.Transform.value = \
            avango.gua.make_trans_mat(0.0,0.0,self.ray_length * -0.5) * \
            avango.gua.make_rot_mat(-90.0,1,0,0) * \
            avango.gua.make_scale_mat(self.ray_thickness, self.ray_length, self.ray_thickness)
        self.ray_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0,0.0,0.0,1.0))
        self.pointer_node.Children.value.append(self.ray_geometry)


        self.intersection_geometry = _loader.create_geometry_from_file("intersection_geometry", "data/objects/sphere.obj", avango.gua.LoaderFlags.DEFAULTS)
        self.intersection_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0,0.0,0.0,1.0))
        SCENEGRAPH.Root.value.Children.value.append(self.intersection_geometry)


        ### set initial states ###
        self.enable(False)



    ### functions ###
    def enable(self, BOOL): # extend respective base-class function
        ManipulationTechnique.enable(self, BOOL) # call base-class function

        if self.enable_flag == False:
            self.intersection_geometry.Tags.value = ["invisible"] # set intersection point invisible


    def update_ray_visualization(self, PICK_WORLD_POS = None, PICK_DISTANCE = 0.0):
        if PICK_WORLD_POS is None: # nothing hit
            self.ray_geometry.Transform.value = \
                avango.gua.make_trans_mat(0.0,0.0,self.ray_length * -0.5) * \
                avango.gua.make_rot_mat(-90.0,1,0,0) * \
                avango.gua.make_scale_mat(self.ray_thickness, self.ray_length, self.ray_thickness)
        
            self.intersection_geometry.Tags.value = ["invisible"] # set intersection point invisible

        else: # something hit
            self.ray_geometry.Transform.value = \
                avango.gua.make_trans_mat(0.0,0.0,PICK_DISTANCE * -0.5) * \
                avango.gua.make_rot_mat(-90.0,1,0,0) * \
                avango.gua.make_scale_mat(self.ray_thickness, PICK_DISTANCE, self.ray_thickness)

            self.intersection_geometry.Tags.value = [] # set intersection point visible
            self.intersection_geometry.Transform.value = avango.gua.make_trans_mat(PICK_WORLD_POS) * avango.gua.make_scale_mat(self.intersection_point_size)


    ### callback functions ###
    def evaluate(self): # implement respective base-class function
        if self.enable_flag == False:
            return
    

        ## calc ray intersection
        _mf_pick_result = self.calc_pick_result(PICK_MAT = self.pointer_node.WorldTransform.value, PICK_LENGTH = self.ray_length)
        #print("hits:", len(_mf_pick_result.value))
    
        if len(_mf_pick_result.value) > 0: # intersection found
            self.pick_result = _mf_pick_result.value[0] # get first pick result
        else: # nothing hit
            self.pick_result = None
        

        ## update visualizations
        if self.pick_result is None:
            self.update_ray_visualization() # apply default ray visualization
        else:
            _node = self.pick_result.Object.value # get intersected geometry node
    
            _pick_pos = self.pick_result.Position.value # pick position in object coordinate system
            _pick_world_pos = self.pick_result.WorldPosition.value # pick position in world coordinate system
    
            _distance = self.pick_result.Distance.value * self.ray_length # pick distance in ray coordinate system
    
            print(_node, _pick_pos, _pick_world_pos, _distance)

        
            self.update_ray_visualization(PICK_WORLD_POS = _pick_world_pos, PICK_DISTANCE = _distance)

        
        ## possibly update object dragging
        self.dragging(_trans_node = self.pointer_node)




class VirtualHand(ManipulationTechnique): #funktioniert

    ## constructor
    def __init__(self):
        self.super(VirtualHand).__init__()


    def my_constructor(self,
        SCENEGRAPH = None,
        NAVIGATION_NODE = None,
        POINTER_TRACKING_STATION = None,
        TRACKING_TRANSMITTER_OFFSET = avango.gua.make_identity_mat(),
        POINTER_DEVICE_STATION = None,
        ):

        ManipulationTechnique.my_constructor(self, SCENEGRAPH, NAVIGATION_NODE, POINTER_TRACKING_STATION, TRACKING_TRANSMITTER_OFFSET, POINTER_DEVICE_STATION) # call base class constructor

        ### further resources ###
        _loader = avango.gua.nodes.TriMeshLoader()


        self.hand_geometry = _loader.create_geometry_from_file("hand_geometry", "data/objects/hand.obj", avango.gua.LoaderFlags.DEFAULTS)
        self.hand_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0, 0.86, 0.54, 1.0))
        self.hand_geometry.Material.value.set_uniform("Emissivity", 0.9)
        self.hand_geometry.Material.value.set_uniform("Metalness", 0.1)
        
        self.hand_transform = avango.gua.nodes.TransformNode(Name = "hand_transform")
        self.hand_transform.Children.value = [self.hand_geometry]
        SCENEGRAPH.Root.value.Children.value.append(self.hand_transform)



        
        ### set initial states ###
        self.enable(False)

    ### functions ###
    def enable(self, BOOL): # extend respective base-class function
        ManipulationTechnique.enable(self, BOOL) # call base-class function

        if self.enable_flag == False:
            pass

   
    ### callback functions ###
    def evaluate(self): # implement respective base-class function
        if self.enable_flag == False:
            return

        _mf_pick_result = self.calc_pick_result(PICK_MAT = self.pointer_node.WorldTransform.value)
    
        if len(_mf_pick_result.value) > 0: # intersection found
            self.pick_result = _mf_pick_result.value[0] # get first pick result
        else: # nothing hit
            self.pick_result = None
        
        self.hand_transform.Transform.value =  self.pointer_node.WorldTransform.value

        
        ## possibly update object dragging
        self.dragging(_trans_node = self.pointer_node)

        


class GoGo(ManipulationTechnique): #effektiv HOMER aber mit Treshhold

    ## constructor
    def __init__(self):
        self.super(GoGo).__init__()

    def my_constructor(self,
        SCENEGRAPH = None,
        NAVIGATION_NODE = None,
        POINTER_TRACKING_STATION = None,
        TRACKING_TRANSMITTER_OFFSET = avango.gua.make_identity_mat(),
        POINTER_DEVICE_STATION = None,
        HEAD_NODE = None,
        ):

        ManipulationTechnique.my_constructor(self, SCENEGRAPH, NAVIGATION_NODE, POINTER_TRACKING_STATION, TRACKING_TRANSMITTER_OFFSET, POINTER_DEVICE_STATION) # call base class constructor


        ### external references ###
        self.NAVIGATION_NODE = NAVIGATION_NODE
        self.HEAD_NODE = HEAD_NODE


        ### additional parameters ###

        self.intersection_point_size = 0.01 # in meter


        self.gogo_threshold = 0.35 # in meter

        self.hand_to_pointer_offset = 1.0
        self.ray_length = 0.0
        self.ray_thickness = 0.0075 # in meter
        self.old_pointer_pos = avango.gua.make_identity_mat
        self.counter = 1.0
        self.calc = 1.0


       
        
        ### further resources ###
        _loader = avango.gua.nodes.TriMeshLoader()


        self.hand_geometry = _loader.create_geometry_from_file("hand_geometry", "data/objects/hand.obj", avango.gua.LoaderFlags.DEFAULTS)
        self.hand_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0, 0.86, 0.54, 1.0))
        self.hand_geometry.Material.value.set_uniform("Emissivity", 0.9)
        self.hand_geometry.Material.value.set_uniform("Metalness", 0.1)
        
        self.hand_transform = avango.gua.nodes.TransformNode(Name = "hand_transform")
        self.hand_transform.Children.value = [self.hand_geometry]
        SCENEGRAPH.Root.value.Children.value.append(self.hand_transform)


        
        ### set initial states ###
        self.enable(False)


    ### callback functions ###
    def evaluate(self): # implement respective base-class function
        
        if self.enable_flag == False:
            return

        self.head_to_pointer_offset = self.HEAD_NODE.WorldTransform.value.get_translate().z - self.pointer_node.WorldTransform.value.get_translate().z

        if self.head_to_pointer_offset<0 :
            self.head_to_pointer_offset = self.hand_to_pointer_offset * -1

        self.hand_to_pointer_offset = self.hand_transform.WorldTransform.value.get_translate().z - self.pointer_node.WorldTransform.value.get_translate().z

        if self.hand_to_pointer_offset<0 :
            self.hand_to_pointer_offset = self.hand_to_pointer_offset * -1

        _mf_pick_result = self.calc_pick_result(PICK_MAT = self.hand_transform.WorldTransform.value, PICK_LENGTH = self.hand_to_pointer_offset)
    
        if len(_mf_pick_result.value) > 0: # intersection found
            self.pick_result = _mf_pick_result.value[0] # get first pick result
        else: # nothing hit
            self.pick_result = None

        if self.head_to_pointer_offset > self.gogo_threshold:
            self.hand_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0, 0.0, 1.0, 1.0))
            
            self.calc = (math.pow(self.pointer_node.WorldTransform.value.get_translate().z, self.head_to_pointer_offset-self.gogo_threshold)- 1)
            self.hand_transform.Transform.value =  self.pointer_node.WorldTransform.value * avango.gua.make_trans_mat(0.0,0.0,self.calc)
            self.pointer_node.Transform.value.get_translate().z = self.hand_transform.WorldTransform.value.get_translate().z
        else:
            self.hand_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0, 0.86, 0.54, 1.0))
            self.hand_transform.Transform.value =  self.pointer_node.WorldTransform.value

        if self.pick_result != None:
            _node = self.pick_result.Object.value
            _pick_pos = self.pick_result.Position.value # pick position in object coordinate system
            _pick_world_pos = self.pick_result.WorldPosition.value
            #_node.Parent.value.WorldTransform.value = avango.gua.make_trans_mat(self.hand_transform.WorldTransform.value.get_translate())
            #print("_node.Parent.value.WorldTransform.value.get_translate().z ", _node.Parent.value.WorldTransform.value.get_translate().z)
            #print("self.hand_transform.WorldTransform.value.get_translate().z ", self.hand_transform.WorldTransform.value.get_translate().z)
            

        
        ## possibly update object dragging
        self.dragging(_trans_node = self.hand_transform, offset = self.hand_to_pointer_offset)

    def start_dragging(self, NODE):
        self.dragged_node = NODE        
        self.dragging_offset_mat = avango.gua.make_inverse_mat(self.hand_transform.WorldTransform.value) * self.dragged_node.WorldTransform.value # object transformation in pointer coordinate system



class Homer(ManipulationTechnique): #ray-controll, aber nach Pick Hand mit "unserem" Homer

    ## constructor
    def __init__(self):
        self.super(Homer).__init__()

    def my_constructor(self,
        SCENEGRAPH = None,
        NAVIGATION_NODE = None,
        POINTER_TRACKING_STATION = None,
        TRACKING_TRANSMITTER_OFFSET = avango.gua.make_identity_mat(),
        POINTER_DEVICE_STATION = None,
        HEAD_NODE = None,
        ):

        ManipulationTechnique.my_constructor(self, SCENEGRAPH, NAVIGATION_NODE, POINTER_TRACKING_STATION, TRACKING_TRANSMITTER_OFFSET, POINTER_DEVICE_STATION) # call base class constructor


        ### external references ###
        self.NAVIGATION_NODE = NAVIGATION_NODE
        self.HEAD_NODE = HEAD_NODE


        ### additional parameters ###

        self.intersection_point_size = 0.01 # in meter


        self.gogo_threshold = 0.35 # in meter

        self.hand_to_pointer_offset = 1.0
        self.ray_length = 5.0
        self.ray_thickness = 0.0075 # in meter
        self.old_pointer_pos = avango.gua.make_identity_mat
        self.counter = 1.0
        self.calc = 1.0
       
        
        ### further resources ###
        _loader = avango.gua.nodes.TriMeshLoader()

        ## ToDo: init hand node(s) here
        # ...

        self.ray_geometry = _loader.create_geometry_from_file("ray_geometry", "data/objects/cylinder.obj", avango.gua.LoaderFlags.DEFAULTS)
        self.ray_transform = avango.gua.nodes.TransformNode(Name="ray_transform")
        self.ray_transform.Transform.value = \
            avango.gua.make_trans_mat(0.0,0.0,self.ray_length * -0.5) * \
            avango.gua.make_rot_mat(-90.0,1,0,0) * \
            avango.gua.make_scale_mat(self.ray_thickness, self.ray_length, self.ray_thickness)
        self.ray_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0,0.0,0.0,1.0))
        self.ray_transform.Children.value.append(self.ray_geometry)
        self.pointer_node.Children.value.append(self.ray_transform)
        self.ray_geometry.Tags.value = ["invisible"]


        self.hand_geometry = _loader.create_geometry_from_file("hand_geometry", "data/objects/hand.obj", avango.gua.LoaderFlags.DEFAULTS)
        #self.hand_geometry.Transform.value = \
        #    avango.gua.make_rot_mat(45.0,1,0,0) * \
        #    avango.gua.make_rot_mat(180.0,0,1,0) * \
        #    avango.gua.make_scale_mat(0.06)
        self.hand_geometry.Material.value.set_uniform("Color", avango.gua.Vec4(1.0, 0.86, 0.54, 1.0))
        self.hand_geometry.Material.value.set_uniform("Emissivity", 0.9)
        self.hand_geometry.Material.value.set_uniform("Metalness", 0.1)
        
        self.hand_transform = avango.gua.nodes.TransformNode(Name = "hand_transform")
        self.hand_transform.Children.value = [self.hand_geometry]
        #self.hand_transform.Transform.value = avango.gua.make_trans_mat(0,0,self.ray_length)
        SCENEGRAPH.Root.value.Children.value.append(self.hand_transform)
        #self.hand_transform.Tags.value = ["visible"]


        
        ### set initial states ###
        self.enable(False)


    def update_ray_visualization(self, PICK_WORLD_POS = None, PICK_DISTANCE = 0.0):
        head_z = self.HEAD_NODE.WorldTransform.value.get_translate().z
        mouse_z = self.pointer_node.WorldTransform.value.get_translate().z

        distance = head_z - mouse_z
        if distance < 0:
            distance = distance * -1


        self.ray_transform.Transform.value = \
            avango.gua.make_trans_mat(0.0,0.0,self.ray_length * -0.5) * \
            avango.gua.make_rot_mat(-90.0,1,0,0) * \
            avango.gua.make_scale_mat(self.ray_thickness, self.ray_length, self.ray_thickness)
    
        self.hand_geometry.Tags.value = ["visible"] # set intersection point invisible
        self.calc = (math.pow(head_z, distance) - 1)
        print("calc: ", self.calc)
        self.ray_length = math.pow(self.calc,5.0)
        self.hand_transform.Transform.value =  self.pointer_node.WorldTransform.value * avango.gua.make_trans_mat(0.0,0.0,self.calc) * avango.gua.make_trans_mat(0,0,self.ray_length*-1)
        #print(self.hand_transform.Transform.value.get_translate().z)
    ### callback functions ###
    def evaluate(self): # implement respective base-class function
        
        ## ToDo: init behavior here (use a short ray for object selection --> e.g. 10cm)
        # ...
        if self.enable_flag == False:
            return
    
        #print(self.hand_transform.Transform.value)
        ## calc ray intersection

        self.hand_to_pointer_offset = self.hand_transform.WorldTransform.value.get_translate().z - self.pointer_node.WorldTransform.value.get_translate().z

        if self.hand_to_pointer_offset<0 :
            self.hand_to_pointer_offset = self.hand_to_pointer_offset * -1

        print("ray_length: ", self.ray_length)
        _mf_pick_result = self.calc_pick_result(PICK_MAT = self.pointer_node.WorldTransform.value, PICK_LENGTH = self.hand_to_pointer_offset)
        #print("hits:", len(_mf_pick_result.value))

        #print("hand_transform: ", self.hand_transform.Transform.value.get_translate().z)
        #print("pick_result: ", _mf_pick_result.value)
    
        if len(_mf_pick_result.value) > 0: # intersection found
            self.pick_result = _mf_pick_result.value[0] # get first pick result
        else: # nothing hit
            self.pick_result = None
        

        ## update visualizations
        if self.pick_result is None:
            self.update_ray_visualization() # apply default ray visualization
        else:
            _node = self.pick_result.Object.value # get intersected geometry node
    
            _pick_pos = self.pick_result.Position.value # pick position in object coordinate system
            _pick_world_pos = self.pick_result.WorldPosition.value # pick position in world coordinate system
    
            _distance = self.pick_result.Distance.value * self.hand_to_pointer_offset # pick distance in ray coordinate system
    
            #print(_node, _pick_pos, _pick_world_pos, _distance)

        
            self.update_ray_visualization(PICK_WORLD_POS = _pick_world_pos, PICK_DISTANCE = _distance)

        
        ## possibly update object dragging
        self.dragging(_trans_node = self.hand_transform)
