# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
	'name': "rInstances",
	'author': "PLyczkowski",
	'version': (1, 0, 0),
	'blender': (2, 7, 6),
	'api': 41270,
	'location': "View3D > Toolbar > Relations",
	'warning': "Addon creates a new scene called rInstance Storage. Please don't touch it!",
	'description': "Convert objects to group instances instantly.",
	'wiki_url': "",
	'tracker_url': "",
	'category': 'Object'}

import bpy,bmesh
from bpy.props import EnumProperty

RSCENE = "rInstance Storage"
RGROUP = "rGroup"

class TurnToRInstance(bpy.types.Operator):
	'''Tooltip'''
	bl_description = "TODO"
	bl_idname = "object.turn_to_rinstance"
	bl_label = "Selection to Instance"
	bl_options = {'REGISTER', 'UNDO'}

	container_name = bpy.props.StringProperty(name="Name", default="Instance")
	use_rotation_from_active = bpy.props.BoolProperty(name="Rotation from Active", default=True)

	pivot_placement = EnumProperty(
        name = "Pivot Placement",
        items = (('MEDIAN', 'Median', ''),
                ('ACTIVE', 'Active', ''),
                ('CURSOR', 'Cursor', '')
                ),
        default = 'MEDIAN'
    )

	@classmethod
	def poll(cls, context):
		
		found_bad_one = False

		for obj in bpy.context.selected_objects:
			if  obj.parent != None:
				found_bad_one = True

		if found_bad_one:
			return False
		else:
			return True

	def execute(self, context):

		contents = bpy.context.selected_objects
		active = bpy.context.scene.objects.active

		storeCursorX = context.space_data.cursor_location.x
		storeCursorY = context.space_data.cursor_location.y
		storeCursorZ = context.space_data.cursor_location.z

		if self.pivot_placement == "MEDIAN":
			bpy.ops.view3d.snap_cursor_to_selected()
		elif self.pivot_placement == "ACTIVE":
			bpy.ops.view3d.snap_cursor_to_active()

		#store rotation
		bpy.ops.object.select_all(action='DESELECT')
		bpy.ops.object.empty_add(type='PLAIN_AXES')
		empty_rotation_saver = bpy.context.active_object
		empty_rotation_saver.rotation_euler = active.rotation_euler

		#add empty
		bpy.ops.object.select_all(action='DESELECT')
		bpy.ops.object.empty_add(type='PLAIN_AXES')
		empty_obj = bpy.context.active_object
		
		#copy rotation from active
		if self.use_rotation_from_active:
			bpy.ops.object.select_all(action='DESELECT')
			empty_obj.select = True
			empty_obj.rotation_euler = empty_rotation_saver.rotation_euler

		#Parent the contents to empty
		for obj in contents:
			obj.select = True
			obj.parent = empty_obj
		bpy.context.scene.objects.active = empty_obj
		empty_obj.select = True
		bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

		#move to center
		bpy.ops.object.select_all(action='DESELECT')
		empty_obj.select = True
		bpy.ops.object.location_clear()
		bpy.ops.object.rotation_clear()

		#unparent
		bpy.ops.object.select_all(action='DESELECT')
		for obj in contents:
			obj.select = True
			bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

		#delete empty
		bpy.ops.object.select_all(action='DESELECT')
		empty_obj.select = True
		bpy.ops.object.delete(use_global=False)

		#add group
		bpy.ops.object.select_all(action='DESELECT')
		for obj in contents:
			obj.select = True
		bpy.ops.group.create(name = RGROUP)

		#get newest rgroup
		group = bpy.context.selected_objects[0].users_group[0]

		# Try to get or create new rscene
		rscene = get_or_create_rscene(context)

		#move to an rscene
		bpy.ops.object.select_all(action='DESELECT')
		for obj in contents:
			obj.select = True
			bpy.ops.object.make_links_scene(scene=RSCENE)
			bpy.ops.object.delete(use_global=False)

		#add instace
		bpy.ops.object.empty_add(type='PLAIN_AXES')
		instance_empty = bpy.context.scene.objects.active
		bpy.context.object.name = self.container_name
		bpy.context.object.empty_draw_size = 0.01
		bpy.context.object.dupli_type = 'GROUP'
		bpy.context.object.dupli_group = bpy.data.groups[group.name]
		instance_empty["is_rinstance"] = True

		#restore rotation
		if self.use_rotation_from_active:
			bpy.context.object.rotation_euler = empty_rotation_saver.rotation_euler

		#clean up
		bpy.ops.object.select_all(action='DESELECT')
		empty_rotation_saver.select = True
		bpy.ops.object.delete(use_global=False)
		bpy.ops.object.clean_up_rinstances()

		#restore cursor
		context.space_data.cursor_location.x = storeCursorX
		context.space_data.cursor_location.y = storeCursorY
		context.space_data.cursor_location.z = storeCursorZ

		#select instance
		instance_empty.select = True

		return {'FINISHED'}

class ReleaseRInstance(bpy.types.Operator):
	'''Tooltip'''
	bl_description = "TODO"
	bl_idname = "object.release_rinstance"
	bl_label = "Release Selected"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		
		found_bad_one = False

		for obj in bpy.context.selected_objects:
			if  obj.type == "EMPTY" and obj.get('is_rinstance') is not None and obj.dupli_type == 'GROUP':
				pass
			else:
				found_bad_one = True

		if found_bad_one:
			return False
		else:
			return True

	def execute(self, context):

		selected = bpy.context.selected_objects
		rscene = get_rscene(context)
		current_scene = bpy.context.window.screen.scene

		released_objects = []

		bpy.ops.object.select_all(action='DESELECT')

		for obj in selected:

			#make sure it's an rinstance
			if obj.get('is_rinstance') is not None and obj.type == "EMPTY" and obj.dupli_type == 'GROUP':

				#get rinstance
				target_rinstance = obj

				#get target rgroup
				target_rgroup = obj.dupli_group

				bpy.ops.object.empty_add(type='PLAIN_AXES')
				instance_replacement_empty = bpy.context.scene.objects.active
				instance_replacement_empty.rotation_euler = target_rinstance.rotation_euler
				instance_replacement_empty.location = target_rinstance.location
				bpy.ops.object.select_all(action='DESELECT')

				#switch to rscene
				bpy.context.window.screen.scene = rscene

				#deselect all
				bpy.ops.object.select_all(action='DESELECT')

				#select if in rgroup
				for obj in rscene.objects:

					for group in obj.users_group: # All groups on object

						if group == target_rgroup:

							obj.select = True

				bpy.ops.object.make_links_scene(scene=current_scene.name)

				#switch back to current scene
				bpy.context.window.screen.scene = current_scene

				rgroup_contents = bpy.context.selected_objects

				#make single user without losing user's groups
				bpy.ops.object.select_all(action='DESELECT')

				#TODO
				# for obj in rgroup_contents:
				# 	obj.select = True
				# 	bpy.context.scene.objects.active = obj
				# 	store_groups = obj.users_group
				# 	bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=False, material=False, texture=False, animation=False)
					

				# 	for group in store_groups:
				# 		bpy.ops.object.group_link(group=group.name)


				# 	bpy.ops.group.objects_remove(target_rgroup)

				#currently selected - linked from rscene
				for obj in rgroup_contents:
					obj.select = True

				# bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=False, material=False, texture=False, animation=False)
				# rgroup_contents = bpy.context.selected_objects

				#parent to empty
				bpy.ops.object.select_all(action='DESELECT')
				bpy.ops.object.empty_add(type='PLAIN_AXES')
				relocation_empty = bpy.context.scene.objects.active

				#parent rgroup contents to relocation empty
				for obj in rgroup_contents:
					obj.parent = relocation_empty

				#relocate to instance replacement empty
				relocation_empty.location = instance_replacement_empty.location
				relocation_empty.rotation_euler = instance_replacement_empty.rotation_euler

				#unparent rgroup contents
				bpy.ops.object.select_all(action='DESELECT')
				for obj in rgroup_contents:
					obj.select = True
					bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

				#store rgroup contents
				for obj in rgroup_contents:
					released_objects.append(obj)

				#clean up
				bpy.ops.object.select_all(action='DESELECT')
				instance_replacement_empty.select = True
				relocation_empty.select = True
				target_rinstance.select = True
				bpy.ops.object.delete(use_global=False)

		# reselect the rinstances contents here
		bpy.ops.object.select_all(action='DESELECT')
		for obj in released_objects:
			obj.select = True

		bpy.ops.object.clean_up_rinstances()

		return {'FINISHED'}

class OpenRInstance(bpy.types.Operator):
	'''Tooltip'''
	bl_description = "TODO"
	bl_idname = "object.open_rinstance"
	bl_label = "Open Instance"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):

		found_bad_one = False

		for obj in bpy.context.selected_objects:
			if  obj.type == "EMPTY" and obj.get('is_rinstance') is not None and obj.dupli_type == 'GROUP':
				pass
			else:
				found_bad_one = True

		if found_bad_one:
			return False
		else:
			return True

	def execute(self, context):

		selected = bpy.context.selected_objects
		rscene = get_rscene(context)
		current_scene = bpy.context.window.screen.scene

		released_empties = []

		bpy.ops.object.select_all(action='DESELECT')

		for obj in selected:

			#make sure it's an rinstance
			if obj.get('is_rinstance') is not None and obj.type == "EMPTY" and obj.dupli_type == 'GROUP':

				#get rinstance
				target_rinstance = obj
				target_rinstance_name = target_rinstance.name
				target_group = target_rinstance.dupli_group

				#store and clear scale
				stored_scaleX = target_rinstance.scale[0]
				stored_scaleY = target_rinstance.scale[1]
				stored_scaleZ = target_rinstance.scale[2]
				target_rinstance.scale = (0,0,0)

				#get target rgroup
				target_rgroup = obj.dupli_group

				#create empty with group stored
				bpy.ops.object.empty_add(type='SPHERE', radius=1, view_align=False, location=(0, 0, 0))
				bpy.context.object.show_x_ray = True
				empty = bpy.context.scene.objects.active
				empty.location = obj.location
				empty.rotation_euler = obj.rotation_euler
				empty["rGroup"] = target_group.name
				empty["opened_rInstance"] = True

				#store empty
				released_empties.append(empty)

				#release rinstance
				bpy.ops.object.select_all(action='DESELECT')
				target_rinstance.select = True
				bpy.ops.object.release_rinstance() #only content selected

				#restore name
				empty.name = target_rinstance_name

				#parent instance content to empty
				empty.select = True
				bpy.context.scene.objects.active = empty
				bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)

				#restore scale
				bpy.context.object.scale[0] = stored_scaleX
				bpy.context.object.scale[1] = stored_scaleY
				bpy.context.object.scale[2] = stored_scaleZ

		#reselect empties
		bpy.ops.object.select_all(action='DESELECT')
		for obj in released_empties:
			obj.select = True
		
		bpy.ops.object.clean_up_rinstances()

		return {'FINISHED'}

class CloseRInstance(bpy.types.Operator):
	'''Tooltip'''
	bl_description = "TODO"
	bl_idname = "object.close_rinstance"
	bl_label = "Close Instance"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):

		found_bad_one = False

		for obj in bpy.context.selected_objects:
			if  obj.type == "EMPTY" and obj.get('opened_rInstance') is not None:
				pass
			else:
				found_bad_one = True

		if found_bad_one:
			return False
		else:
			return True

	def execute(self, context):

		selected = bpy.context.selected_objects
		rscene = get_rscene(context)
		current_scene = bpy.context.window.screen.scene

		storeCursorX = context.space_data.cursor_location.x
		storeCursorY = context.space_data.cursor_location.y
		storeCursorZ = context.space_data.cursor_location.z

		bpy.ops.object.select_all(action='DESELECT')

		for open_rinstance in selected:

			#get rinstance data
			open_rinstance.select = True
			bpy.context.scene.objects.active = open_rinstance
			target_rgroup = open_rinstance.get('rGroup')
			open_rinstance_name = open_rinstance.name

			#get new_rinstance_content
			new_rinstance_content = open_rinstance.children

			#place cursor
			bpy.ops.view3d.snap_cursor_to_active()

			#store and clear scale
			stored_scaleX = open_rinstance.scale[0]
			stored_scaleY = open_rinstance.scale[1]
			stored_scaleZ = open_rinstance.scale[2]
			bpy.ops.object.scale_clear()

			#select children
			bpy.ops.object.select_all(action='DESELECT')
			for obj in new_rinstance_content:
				obj.select = True
				bpy.context.scene.objects.active = obj
				bpy.ops.object.group_link(group=target_rgroup)

				#clear parent
				bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

			#clean rGroup from rScene
			rscene = get_or_create_rscene(context)

			if rscene is not None:

				bpy.context.window.screen.scene = rscene

				bpy.ops.object.select_all(action='DESELECT')

				for obj in rscene.objects: # All objects in rscene

					is_in_target_rgroup = False

					for group in obj.users_group: # All groups on object

						if group.name == target_rgroup:

							is_in_target_rgroup = True

					if is_in_target_rgroup:

						obj.select = True
						bpy.ops.object.delete()

			bpy.context.window.screen.scene = current_scene

			#add empty
			bpy.ops.object.select_all(action='DESELECT')
			bpy.ops.object.empty_add(type='PLAIN_AXES')
			empty_obj = bpy.context.active_object
			
			#copy rotation from active
			empty_obj.rotation_euler = open_rinstance.rotation_euler

			#Parent the new_rinstance_content to empty
			for obj in new_rinstance_content:
				obj.select = True
				obj.parent = empty_obj
			bpy.context.scene.objects.active = empty_obj
			empty_obj.select = True
			bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

			#move to center
			bpy.ops.object.select_all(action='DESELECT')
			empty_obj.select = True
			bpy.ops.object.location_clear()
			bpy.ops.object.rotation_clear()

			#unparent
			bpy.ops.object.select_all(action='DESELECT')
			for obj in new_rinstance_content:
				obj.select = True
				bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

			#delete empty
			bpy.ops.object.select_all(action='DESELECT')
			empty_obj.select = True
			bpy.ops.object.delete(use_global=False)

			#add group
			bpy.ops.object.select_all(action='DESELECT')
			for obj in new_rinstance_content:
				obj.select = True
			bpy.ops.group.create(name = RGROUP)

			#get newest rgroup
			group = bpy.context.selected_objects[0].users_group[0]

			# Try to get or create new rscene
			rscene = get_or_create_rscene(context)

			#move to an rscene
			bpy.ops.object.select_all(action='DESELECT')
			for obj in new_rinstance_content:
				obj.select = True
				bpy.ops.object.make_links_scene(scene=RSCENE)
				bpy.ops.object.delete(use_global=False)

			#add instace
			bpy.ops.object.empty_add(type='PLAIN_AXES')
			instance_empty = bpy.context.scene.objects.active
			bpy.context.object.empty_draw_size = 0.01
			bpy.context.object.dupli_type = 'GROUP'
			bpy.context.object.dupli_group = bpy.data.groups[group.name]
			instance_empty["is_rinstance"] = True

			#restore rotation
			bpy.context.object.rotation_euler = open_rinstance.rotation_euler

			#restore scale
			bpy.context.object.scale[0] = stored_scaleX
			bpy.context.object.scale[1] = stored_scaleY
			bpy.context.object.scale[2] = stored_scaleZ

			#clean up
			bpy.ops.object.select_all(action='DESELECT')
			open_rinstance.select = True
			bpy.ops.object.delete(use_global=False)
			instance_empty.name = open_rinstance_name

		#restore cursor
		context.space_data.cursor_location.x = storeCursorX
		context.space_data.cursor_location.y = storeCursorY
		context.space_data.cursor_location.z = storeCursorZ
		
		bpy.ops.object.clean_up_rinstances()

		return {'FINISHED'}

class RInstancesToObjects(bpy.types.Operator):
	'''Tooltip'''
	bl_description = "TODO"
	bl_idname = "object.rinstances_to_objects"
	bl_label = "Release Hierarchy"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):

		found_bad_one = False

		for obj in bpy.context.selected_objects:
			if  obj.type == "EMPTY" and obj.get('is_rinstance') is not None and obj.dupli_type == 'GROUP':
				pass
			else:
				found_bad_one = True

		if found_bad_one:
			return False
		else:
			return True

	def execute(self, context):

		#replace make_real with manual duplicate objects from group and place over instances

		#make duplicates real
		for obj in bpy.context.selected_objects:

			if obj.get('is_rinstance') is not None:

				bpy.ops.object.duplicates_make_real()

		selected = bpy.context.selected_objects

		#remove empties
		for obj in selected:

			if obj.get('is_rinstance') is not None:

				bpy.ops.object.select_all(action='DESELECT')
				obj.select = True
				bpy.ops.object.delete(use_global=False)

		#reselect rest
		for obj in selected:
			obj.select = True

		bpy.ops.object.clean_up_rinstances()

		return {'FINISHED'}

class CleanUpRInstances(bpy.types.Operator):
	'''Tooltip'''
	bl_description = "Deletes all objects in the storage that do not have an instance."
	bl_idname = "object.clean_up_rinstances"
	bl_label = "Clean Up Instances"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return True

	def execute(self, context):

		rscene = get_rscene(context)
		current_scene = bpy.context.window.screen.scene

		selected = bpy.context.selected_objects
		bpy.ops.object.select_all(action='DESELECT')

		bpy.context.window.screen.scene = rscene

		bpy.ops.object.select_all(action='DESELECT')

		if rscene is not None:

			for obj in rscene.objects: # All objects in rscene

				got_instance = False
				
				for group in obj.users_group: # All groups on object

					# if RGROUP in group.name:

					for obj2 in bpy.data.objects:

						if obj2.type == "EMPTY" and obj2.dupli_type == 'GROUP' and obj2.dupli_group == group:

							got_instance = True

				if got_instance == False:

					print("rInstance object "+obj.name+" is orphaned, deleting.")
					obj.select = True
					bpy.ops.object.delete()

		bpy.context.window.screen.scene = current_scene

		#reselect what was selected
		for obj in selected:
			obj.select = True

		return {'FINISHED'}

#########
# DEF'S #
#########

def get_rscene(context):
	rscene_name = RSCENE

	if rscene_name in bpy.data.scenes:
		return bpy.data.scenes[rscene_name]
	else:
		return None

def get_or_create_rscene(context):
	rscene_name = RSCENE

	if rscene_name in bpy.data.scenes:
		return bpy.data.scenes[rscene_name]
	else:
		return bpy.data.scenes.new(rscene_name)
	return None

######
# UI #
######

class addButtonsInObjectMode(bpy.types.Panel):
	bl_idname = "rInstances"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = "Relations"

	bl_label = "rInstances"
	bl_context = "objectmode"

	def draw(self, context):
		layout = self.layout

		col = layout.column(align=True)

		col.operator("object.turn_to_rinstance")
		col.operator("object.release_rinstance")
		col = layout.column(align=True)
		col.operator("object.open_rinstance")
		col.operator("object.close_rinstance")
		col = layout.column(align=True)
		col.operator("object.rinstances_to_objects")
		
		# found_parent = False
		# for obj in bpy.context.selected_objects:
		# 	if  obj.parent != None:
		# 		found_parent = True

		# if found_parent:
		# 	layout.label(icon="ERROR", text="Parent data won't be preserved!")

############
# REGISTER #
############

def register():

	bpy.utils.register_module(__name__)

def unregister():

	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()