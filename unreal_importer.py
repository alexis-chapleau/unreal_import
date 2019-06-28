import abc
import argparse
import os

import unreal

from fp_utils import paths, fpfs

"""
Strategy Pattern
"""


class CreateImportTaskStrategy(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def build_import_options(self, entity):
        pass

    @abc.abstractproperty
    def destination_path(self):
        pass

    def create_import_task(self, entity):
        """

        :param entity: ImportData instance
        :return:
        """
        options = self.build_import_options()

        task = unreal.AssetImportTask()
        task.set_editor_property('options', options)
        task.set_editor_property('automated', True)
        task.set_editor_property('filename', entity.to_string())
        task.set_editor_property('destination_name', entity.name)
        task.set_editor_property('destination_path', self.destination_path)
        task.set_editor_property('save', True)
        task.set_editor_property('replace_existing', True)
        return task


class SkeletalImportTaskStrategy(CreateImportTaskStrategy):

    # skeleton_path
    @staticmethod
    def build_import_options():
        options = unreal.FbxImportUI()
        #  ---- MESH
        options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_as_skeletal', True)  # Static Mesh
        options.skeletal_mesh_import_data.set_editor_property('vertex_color_import_option',
                                                              unreal.VertexColorImportOption.REPLACE)
        options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose', True)
        options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose', True)
        options.skeletal_mesh_import_data.set_editor_property('preserve_smoothing_groups', True)
        options.skeletal_mesh_import_data.set_editor_property('import_meshes_in_bone_hierarchy', True)
        options.skeletal_mesh_import_data.set_editor_property('import_morph_targets', False)
        options.skeletal_mesh_import_data.set_editor_property('import_mesh_lo_ds', False)
        options.skeletal_mesh_import_data.set_editor_property('normal_import_method',
                                                              unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)

        # ---- Transform
        options.skeletal_mesh_import_data.set_editor_property('import_translation', unreal.Vector(0.0, 0.0, 0.0))
        options.skeletal_mesh_import_data.set_editor_property('import_rotation', unreal.Rotator(0.0, 0.0, 0.0))
        options.skeletal_mesh_import_data.set_editor_property('import_uniform_scale', 1.0)
        # ---- Miscellaneous
        options.skeletal_mesh_import_data.set_editor_property('convert_scene', True)
        options.skeletal_mesh_import_data.set_editor_property('force_front_x_axis', False)
        options.skeletal_mesh_import_data.set_editor_property('convert_scene_unit', True)
        options.set_editor_property('override_full_name', True)

        return options

    @property
    def destination_path(self):
        return '/Game/Skeletal'


class StaticImportTaskStrategy(CreateImportTaskStrategy):

    @staticmethod
    def build_import_options():
        options = unreal.FbxImportUI()

        #  ---- MESH
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_as_skeletal', False)  # Static Mesh
        options.static_mesh_import_data.set_editor_property('auto_generate_collision', False)
        # ---- Transform
        options.static_mesh_import_data.set_editor_property('import_translation', unreal.Vector(0.0, 0.0, 0.0))
        options.static_mesh_import_data.set_editor_property('import_rotation', unreal.Rotator(0.0, 0.0, 0.0))
        options.static_mesh_import_data.set_editor_property('import_uniform_scale', 1.0)
        # ---- Miscellaneous
        options.static_mesh_import_data.set_editor_property('convert_scene', True)
        options.static_mesh_import_data.set_editor_property('force_front_x_axis', False)
        options.static_mesh_import_data.set_editor_property('convert_scene_unit', True)
        options.set_editor_property('override_full_name', True)

        return options

    @property
    def destination_path(self):
        return '/Game/Static'


class ExecuteTaskStrategy(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def execute_task(self, task):
        pass


class AssetExecuteTaskStrategy(ExecuteTaskStrategy):

    def execute_task(self, task):
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported_asset_paths = []
        for path in task.get_editor_property('imported_object_paths'):
            imported_asset_paths.append(UAssetData(path))
        return imported_asset_paths


class Data(object):
    __metaclass__ = abc.ABCMeta

    def __repr__(self):
        return '{}:{}\n{}'.format(self.__class__.__name__, id(self),
                                  " ".join("{}={!r}".format(k, v) for k, v in self.__dict__.items()))

    @abc.abstractproperty
    def path(self):
        pass

    def to_string(self):
        return self.path.to_string()


class ImportData(Data):

    def __init__(self, filePath='', fileName='', fileType=''):
        self.name = fileName
        self.type = fileType
        self._filepath = filePath

        self._path = None

    @property
    def path(self):
        if not self._path:
            self._path = paths.FilePath(self._filepath)
        return self._path


class UAssetData(Data):

    def __init__(self, project_path=''):
        self.project_path = project_path
        self._system_path = None

    @property
    def path(self):
        if not self._system_path:
            root_path = unreal.Paths.project_dir()
            uasset_path = self._convert_to_system_path(self.project_path)
            self._system_path = paths.FilePath(root_path + uasset_path)
        return self._system_path

    def _convert_to_system_path(self, path):
        content_path = path.replace(r'/Game', 'Content')
        system_path = content_path.split('.')[0] + '.uasset'
        return system_path

    def move(self, dir):
        if not dir.__class__.__name__ == 'Directory':
            dir = paths.Directory(dir)
        fpfs.mv(self.to_string(), dir.to_string())
        self._system_path = dir / self.path.basename


class UnrealImporter(object):

    @classmethod
    def init_from_entity(self, entity):
        """
        Returns a UnrealImporter instance using the appropriate Strategies

        :param entity: ImportData
        :return: UnrealImporter instance.
        """

        if entity.type.lower() == '1_static_mesh':
            return UnrealImporter(entity, StaticImportTaskStrategy(),
                                  AssetExecuteTaskStrategy())

        elif entity.type.lower() == '2_skeletal_mesh':
            return UnrealImporter(entity, SkeletalImportTaskStrategy(),
                                  AssetExecuteTaskStrategy())

        else:
            raise NotImplementedError('No implementation for the "{}" file type'.format(entity.type))

    def __init__(self, entity, create_task_strategy, execute_task_strategy):

        self._file = entity
        self._create_task_strategy = create_task_strategy
        self._execute_task_strategy = execute_task_strategy

    def create_import_task(self, entity):
        return self._create_task_strategy.create_import_task(entity)

    def execute_task(self, task):
        return self._execute_task_strategy.execute_task(task)

    def process(self):
        task = self.create_import_task(self._file)
        imported_objects = self.execute_task(task)
        return imported_objects


def main():
    parser = argparse.ArgumentParser(__file__)
    parser.add_argument('_filepath')
    parser.add_argument('name')
    parser.add_argument('type')
    parser.add_argument('publish_path')

    importData = ImportData()
    args = parser.parse_args(namespace=importData)

    unreal_importer = UnrealImporter.init_from_entity(importData)
    imported_uassets = unreal_importer.process()
    for uasset in imported_uassets:
        uasset.move(args.publish_path)
    return imported_uassets


if __name__ == '__main__':
    main()
