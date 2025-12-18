// This is the pybind11 wrapper for the ATINetft class. It is used to expose the class to Python.

// clang-format off
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/eigen.h>
#include "ati_netft/ati_netft.h"
#include "hardware_interfaces/ft_interfaces.h"

namespace py = pybind11;

PYBIND11_MODULE(ati_netft_pybind, m)
{
    py::class_<ATINetft>(m, "ATINetft")
        .def(py::init<>())
        .def("init", [](ATINetft& self, const ATINetft::ATINetftConfig& config) {
            return self.init(RUT::Clock::now(), config);
        })
        .def("getWrenchSensor", &ATINetft::getWrenchSensor)
        .def("getWrenchTool", &ATINetft::getWrenchTool)
        .def("getWrenchNetTool", &ATINetft::getWrenchNetTool)
        .def("get_wrench_sensor", [](ATINetft& self) {
            RUT::VectorXd wrench = RUT::VectorXd::Zero(6);
            int status = self.getWrenchSensor(wrench);
            return py::make_tuple(status, wrench);
        })
        .def("get_wrench_tool", [](ATINetft& self) {
            RUT::VectorXd wrench = RUT::VectorXd::Zero(6);
            int status = self.getWrenchTool(wrench);
            return py::make_tuple(status, wrench);
        })
        .def("get_wrench_net_tool", [](ATINetft& self, const RUT::Vector7d& pose) {
            RUT::VectorXd wrench = RUT::VectorXd::Zero(6);
            int status = self.getWrenchNetTool(pose, wrench);
            return py::make_tuple(status, wrench);
        })
        .def("is_data_ready", &ATINetft::is_data_ready);

    py::class_<ATINetft::ATINetftConfig>(m, "ATINetftConfig")
        .def(py::init<>())
        .def_readwrite("ip_address", &ATINetft::ATINetftConfig::ip_address)
        .def_readwrite("counts_per_force", &ATINetft::ATINetftConfig::counts_per_force)
        .def_readwrite("counts_per_torque", &ATINetft::ATINetftConfig::counts_per_torque)
        .def_readwrite("sensor_name", &ATINetft::ATINetftConfig::sensor_name)
        .def_readwrite("fullpath", &ATINetft::ATINetftConfig::fullpath)
        .def_readwrite("print_flag", &ATINetft::ATINetftConfig::print_flag)
        .def_readwrite("publish_rate", &ATINetft::ATINetftConfig::publish_rate)
        .def_readwrite("noise_level", &ATINetft::ATINetftConfig::noise_level)
        .def_readwrite("stall_threshold", &ATINetft::ATINetftConfig::stall_threshold)
        .def_readwrite("Foffset", &ATINetft::ATINetftConfig::Foffset)
        .def_readwrite("Toffset", &ATINetft::ATINetftConfig::Toffset)
        .def_readwrite("Gravity", &ATINetft::ATINetftConfig::Gravity)
        .def_readwrite("Pcom", &ATINetft::ATINetftConfig::Pcom)
        .def_readwrite("WrenchSafety", &ATINetft::ATINetftConfig::WrenchSafety)
        .def_readwrite("PoseSensorTool", &ATINetft::ATINetftConfig::PoseSensorTool)
        .def("deserialize", &ATINetft::ATINetftConfig::deserialize);
}
// clang-format on
