Name:           yum-plugin-kmod
Version: 1.0.1
Release:        1%{?dist}
Summary:        Yum plugin support for kmod kernel modules

Group:          System Environment/Base
License:        GPLv2+
URL:            http://linuxczar.net/wordpress/projects/fedorakmod
Source0:        fedorakmod-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
Requires:       yum

%description
A Yum plugin to support the Fedora Kmod kernel module packaging standard.

%prep
%setup -q -n fedorakmod-%{version}


%build



%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc README
%{_sysconfdir}/yum/pluginconf.d/*
/usr/lib/yum-plugins/*
/usr/share/fedorakmod/*


%changelog
* Tue Jun 09 2009 Jack Neely <jjneely@ncsu.edu> 1.0.1-1
- Include the kmodtool script used by kmod packages with changes needed
  by fedora 10/11

* Fri Apr 24 2009 Jack Neely <jjneely@ncsu.edu> 1.0.0-1
- Initial repackaging after removal from yum-utils

